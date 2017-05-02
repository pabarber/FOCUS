"""module used to aggregate raw csv files into master datalists ready for analysis of further output"""
import pandas as pd
import os
import glob
import csv
import numpy as np
from collections import defaultdict
import datetime as dt
import math
from bokeh.plotting import ColumnDataSource, figure
from bokeh.io import output_file, save
from bokeh.models import DatetimeTickFormatter, HoverTool
import matplotlib.pyplot as plt


def user_journey_single():
    """a function that allows the user to extract an individual user journey. Simply searches the csv output files that
     exists and prints a sorted list (by time) of events that household experienced"""

    user_list = []
    output_path = "outputs"
    hh_id = input('Enter hh to extract: ')

    folder_list = glob.glob(output_path + '/*/')  # create list of folders at output path

    for folder in folder_list:
        folder_name = folder.split(os.path.sep)[-2]

        glob_folder = os.path.join('outputs', folder_name, '*.csv')
        file_list = glob.glob(glob_folder)  # get a list of all files in the folder

        try:
            for file in file_list:
                file_name = file.split(os.path.sep)[-1][0]

                full_path = os.path.join(output_path, folder_name)
                full_path = full_path + "/" + file_name + ".csv"

                with open(full_path, 'r') as f:
                    reader = csv.DictReader(f)
                    rows = [row for row in reader if row['hh_id'] == hh_id]

                for row in rows:
                    # append folder_name tag
                    row['event'] = folder_name
                    user_list.append(row)

        except:
            pass

    listsorted = sorted(user_list, key=lambda x: float(x['time']))

    for row in listsorted:
        print(row)


def user_journey_all():
    """a summary of all user journeys?"""


def csv_to_pandas(output_path, output_type):
    """converts selected csv output files to a dictionary of dictionaries of Pandas data frames for each output type
    and run. Output_type is a list of the types of output to include (e.g. responses, visits). To refer to the finished
    data_dict use: data_dict['type of output']['run']. Data frame will be every replication of that output type for
    that run"""

    folder_list = glob.glob(output_path + '/*/')  # create list of folders at output path
    data_dict = defaultdict(list)  # create a dict ready for the data frames

    for folder in folder_list:
        folder_name = folder.split(os.path.sep)[-2]
        if folder_name in output_type:

            glob_folder = os.path.join('outputs', folder_name, '*.csv')
            file_list = glob.glob(glob_folder)  # get a list of all files(sim runs) in the folder

            data_dict[folder_name] = defaultdict(list)

            # for each file (sim run) add to dictionary for that type of output
            for file in file_list:
                file_name = file.split(os.path.sep)[-1][0]
                data_dict[folder_name][file_name] = pd.read_csv(file, header=0)  # add each run to dict
    return data_dict


def cumulative_sum(df, start, end, step, geog, resp_type='all'):
    """takes a data frame and returns average cumulative totals for specified geography in correct format for data
     vis teams map template"""

    # create bins and group names to use
    bin_values = np.arange(start, end + step, step)
    group_names = np.arange(start, end, step)

    # filter df to only have correct entries
    if resp_type == 'digital':
        df = df[df['digital'] == True].copy()

    elif resp_type == 'paper':
        df = df[df['digital'] == False].copy()

    # add a new column to passed data frame containing the categories the entry belongs too
    df['categories'] = pd.cut(df['time'], bin_values, labels=group_names)
    # group by each combination of district and category and count the number of each category
    cat_sum = df.groupby([geog, 'categories'])['categories'].size()
    # calculate the cum sum of the totals
    cat_sum = cat_sum.groupby(level=[0]).cumsum().reset_index(name='cum_sum')
    # pivot it so the categories become the columns
    cat_sum_flipped = cat_sum.pivot(index=geog, columns='categories', values='cum_sum')
    # and then add back in any missing categories
    cat_sum_flipped = cat_sum_flipped.reindex(columns=group_names).ffill(axis=1)
    reps = df['rep'].max()
    cat_sum_flipped = cat_sum_flipped.div(reps, axis=0).replace('Nan', 0, regex=True)

    return cat_sum_flipped


def divide_all(data_numerator, data_denominator, runs=()):

    divide_runs = defaultdict(list)

    for key, value in data_numerator.items():
        divide_runs[key] = divide_single(data_numerator[key], data_denominator)

    return divide_runs


def divide_single(data_numerator, data_denominator):

    int_num_df = pd.DataFrame({'numerator_result': data_numerator.groupby(['rep', 'hh_type']).size()}).reset_index()
    out_num_df = pd.DataFrame(int_num_df.groupby(['hh_type']).mean()['numerator_result']).reset_index()

    # add item to divide by do div and keep only new...
    int_den_df = pd.DataFrame({'denominator_result': data_denominator.groupby(['rep', 'hh_type']).size()}).reset_index()
    out_den_df = pd.DataFrame(int_den_df.groupby(['hh_type']).mean()['denominator_result']).reset_index()

    returns = pd.merge(out_num_df, out_den_df, on='hh_type')

    returns['returns'] = returns[['numerator_result']].div(getattr(returns, 'denominator_result'), axis=0)
    returns = returns[['hh_type', 'returns']]

    return returns


def divide_single_count(data_numerator, data_denominator):

    int_num_df = pd.DataFrame({'numerator_result': data_numerator.groupby(['rep', 'district']).size()}).reset_index()
    out_num_df = pd.DataFrame(int_num_df.groupby(['district']).mean()['numerator_result']).reset_index()

    out_den_df = pd.DataFrame(data_denominator.groupby(['district']).mean()['hh_count']).reset_index()

    returns = pd.merge(out_num_df, out_den_df, on='district')

    returns['returns'] = returns[['numerator_result']].div(getattr(returns, 'hh_count'), axis=0)
    returns = returns[['returns']]

    return returns


def add_hh_count(data_lists):

    hh_count = defaultdict(list)

    for df in data_lists['hh_count']:
        hh_count['hh_count'].append(df)

    return hh_count


def add_days(input_date, add_days):

    return input_date + dt.timedelta(days=add_days)


def bin_records(input_df, filter = []):
    """function that takes output files and produces binned data ready for plotting"""
    start_date = dt.date(*map(int, '2011, 3, 6'.split(',')))

    # apply some filters before binning
    # in this case filter out the do nothings and help as they are not returns
    if filter:
        for item in filter:
            input_df = input_df.drop(input_df[(input_df.action == item)].index)

    bins = np.arange(0, 1872, 24).tolist()
    # set group names to be the dates
    group_names = []
    days = len(bins)

    for i in range(0, days-1):
        group_names.append(add_days(start_date, i))

    input_df['categories'] = pd.cut(input_df['time'], bins, labels=group_names)
    counts = pd.value_counts(input_df['categories'])

    return counts


def roundup(x):

    return int(math.ceil(x / 100.0)) * 100


def combined_chart(input1, input2, filename):
    # takes two series and combines to produce a html chart with the filename given

    combined = pd.concat([input1, input2], axis=1)
    combined.reset_index(level=0, inplace=True)
    combined.columns = ['date', 'passive', 'actual']
    combined['date_formatted'] = combined['date'].dt.strftime('%Y-%m-%d')
    max_y = roundup(combined['actual'].max())

    source = ColumnDataSource(combined)

    tools = 'box_zoom,' \
            'crosshair,' \
            'resize,' \
            'reset,' \
            'pan,' \
            'wheel_zoom,' \
            'save'

    # Add lines to the figure p
    p = figure(x_axis_label='Date', y_axis_label='Returns', width=1600, height=800, tools=tools)
    p.line(x='date', y='passive', source=source, color='green', legend='Passive')
    p.line(x='date', y='actual', source=source, color='blue', legend='Actual')

    fu_date = dt.datetime.strptime('2011-04-01', '%Y-%m-%d').date()
    p.line([fu_date, fu_date], [0, max_y], color='red')

    hover = HoverTool(tooltips=
                      [('Passive', '@passive'),
                       ('Actual', '@actual'),
                       ('Date', '@date_formatted')
                       ])

    p.add_tools(hover)

    # do some formatting
    p.xaxis.formatter = DatetimeTickFormatter(
        days=["%d %b %y"]
    )
    p.xaxis.major_label_orientation = math.pi / 4
    p.xaxis.axis_label_text_font_size = '12pt'
    p.xaxis.major_label_text_font_size = '12pt'

    p.yaxis.axis_label_text_font_size = '12pt'
    p.yaxis.major_label_text_font_size = '12pt'

    p.legend.label_text_font_size = '12pt'
    title_text = 'Effect of interventions on ' + filename[:-5]
    p.title.text = title_text

    # Specify the name of the output file and show the result
    output_file(filename)
    save(p)


# for given level of geog to use
def produce_return_charts(df1, df2, filter='E&W'):
    """default is to produce the difference between the passive and the active. ie, the self
    response and response with interventions"""

    if filter == 'E&W':
        # just use the whole df

        passive = bin_records(df1, ['do_nothing', 'help'])
        actual = bin_records(df2)
        combined_chart(passive, actual, 'overall returns.html')

    else:
        # produce for each area

        for district in df1[filter].unique():
            filename = district + ' returns.html'
            # extract just the current LA from the df and pass that to the functions
            df1_temp = df1[df1[filter] == district].copy()
            df2_temp = df2[df2[filter] == district].copy()
            passive = bin_records(df1_temp, ['do_nothing', 'help'])
            actual = bin_records(df2_temp)
            combined_chart(passive, actual, filename)


def active_response(filter='LSOA'):
    # returns a series object that contains a count of the number of results within set limits
    output_list = []

    output_path = os.path.join(os.getcwd(), 'outputs')
    pandas_data = csv_to_pandas(output_path, ['Responded', 'hh_record'])

    df1 = pandas_data['hh_record']['1']  # run 1 all reps if present
    df2 = pandas_data['Responded']['1']

    for item in df1[filter].unique():

        len_df1 = len(df1[df1[filter] == item].copy())
        len_df2 = len(df2[df2[filter] == item].copy())

        output_list.append((len_df2/len_df1)*100)

    # now bin the data
    bins = np.arange(70, 102, 2).tolist()
    # set group names to be the dates

    output_list = pd.cut(output_list, bins)
    counts = pd.value_counts(output_list)

    return counts


def passive_response(filter='LSOA'):
    # returns a series object that contains a count of the number of results within set limits
    output_list = []

    output_path = os.path.join(os.getcwd(), 'outputs')
    pandas_data = csv_to_pandas(output_path, ['Responded', 'hh_record'])

    df1 = pandas_data['hh_record']['1']  # run 1 all reps if present
    df2 = pandas_data['hh_record']['1'].copy()

    # drop the do nothings and helps
    drop_list = ['do_nothing', 'help']

    for item in drop_list:
        df1 = df1.drop(df1[(df1.action == item)].index)

    for item in df1[filter].unique():

        len_df1 = len(df1[df1[filter] == item].copy())
        len_df2 = len(df2[df2[filter] == item].copy())

        output_list.append((len_df1/len_df2)*100)

    # now bin the data
    bins = np.arange(70, 102, 2).tolist()
    # set group names to be the dates

    output_list = pd.cut(output_list, bins)
    counts = pd.value_counts(output_list)

    return counts


def waterfall():
    """ produces parallel horizontal bar charts that display the distribution of response rates achieve from two
     strategies"""

    active_list = active_response()
    passive_list = passive_response()

    combined_list = pd.concat([active_list, passive_list], axis=1)
    combined_list.reset_index(level=0, inplace=True)
    combined_list.columns = ['cat', 'active', 'passive']
    print(combined_list)

    x1 = combined_list['passive'].tolist()
    x2 = combined_list['active'].tolist()
    y = np.arange(70, 100, 2)

    fig, axes = plt.subplots(ncols=2, sharey=True)
    axes[0].barh(y, x1, align='center', color='green', zorder=10)
    axes[0].set(title='passive')
    axes[1].barh(y, x2, align='center', color='blue', zorder=10)
    axes[1].set(title='active')

    axes[0].invert_xaxis()
    axes[0].set(yticks=y, yticklabels=y)
    axes[0].yaxis.tick_right()

    for ax in axes.flat:
        ax.margins(0.03)
        ax.grid(True)

    fig.tight_layout()
    fig.subplots_adjust(wspace=0.09)
    plt.show()
