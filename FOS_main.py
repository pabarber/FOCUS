"""Main control file"""
import sys
import json
import datetime as dt
import random
import simpy
import initialise
import os
import shutil
import post_process
import time
import copy
from collections import defaultdict
from itertools import repeat
from multiprocessing import cpu_count, Pool, freeze_support, Lock
import helper as hp
import pandas as pd

l = Lock()  # global declaration...can I avoid this?


def start_run(run_input, seeds, out_path):

    max_output_file_size = 100000000
    # pull out length of sim for current run
    start_date = dt.date(*map(int, run_input['start_date'].split(',')))
    end_date = dt.date(*map(int, run_input['end_date'].split(',')))
    sim_hours = (end_date - start_date).total_seconds()/3600
    census_date = dt.date(*map(int, run_input['census_date'].split(',')))
    census_day = (census_date - start_date).days

    # write key dates/info to a csv for later use in post processing
    temp_list = [{'rep': run_input['rep id'],
                  'start_date': start_date,
                  'end_date': end_date,
                  'census_date': census_date,
                  'census_day': census_day,
                  'sim_hours': sim_hours}]

    if not os.path.isdir(os.path.join(out_path, 'key info')):
        os.mkdir(os.path.join(out_path, 'key info'))

    if not os.path.isfile(os.path.join(out_path, 'key dates', run_input['run id'] + ".csv")):
        pd.DataFrame(temp_list).to_csv(os.path.join(out_path, 'key info', run_input['run id'] + ".csv"))
    else:
        pd.DataFrame(temp_list).to_csv(os.path.join(out_path, 'key info', run_input['run id'] + ".csv"), mode='a',
                                       header=False)

    output_data = defaultdict(list)

    rnd = random.Random()
    rnd.seed(str(seeds))

    # define simpy env for current rep
    env = simpy.Environment()

    # initialise replication
    initialise.Rep(env,
                   run_input,
                   output_data,
                   rnd,
                   sim_hours,
                   start_date,
                   census_day,
                   out_path,
                   max_output_file_size)

    # and run it
    env.run(until=sim_hours)

    # write the output to csv files
    hp.write_output(output_data, out_path, run_input['run id'])


def produce_default_output(geog='LA'):
    # this produces some default processed data for run 1 only in some cases...
    # defaults to LA level to produce outputs that fit into the Data Vis map format

    # select data to read into data frame structure
    pandas_data = post_process.csv_to_pandas(output_path, ['Return_sent', 'hh_record', 'Responded', 'key info'])

    # gets list if runs - uses hh_record as will always contain all the runs
    runs = sorted(list(pandas_data['hh_record'].keys()))
    for current_run in runs:

        # calculate the total number of households in each area and in total
        hh_count = pandas_data['hh_record'][str(current_run)].groupby(geog).size()  # hh per area
        hh_totals = hh_count.sum()  # total of households

        try:
            # produce cumulative summary of overall returns
            cumulative_returns = post_process.cumulative_sum(pandas_data['Return_sent'][str(current_run)], 0, 1824, 24,
                                                             geog)
            hh_count.index = cumulative_returns.index
            returns_summary = cumulative_returns.div(hh_count, axis='index')
            returns_summary.to_csv(os.path.join(os.getcwd(), 'summary results', "Returns summary run " +
                                                current_run + ".csv"))

            # also need an E+W average for each
            overall_returns = cumulative_returns.sum(axis=0)
            average_returns = (overall_returns / hh_totals) * 100
            average_returns = pd.DataFrame(average_returns).T
            average_returns.to_csv(os.path.join(os.getcwd(), 'summary results', "Average returns run " +
                                                current_run + ".csv"))

        except ValueError as e:
            print(e, " in run: ", current_run)

        try:

            # produce summary of digital returns
            cumulative_dig_returns = post_process.cumulative_sum(pandas_data['Return_sent'][str(current_run)], 0, 1824,
                                                                 24, geog, 'digital')
            hh_count.index = cumulative_dig_returns.index
            dig_returns_summary = cumulative_dig_returns.div(hh_count, axis='index')
            dig_returns_summary.to_csv(os.path.join(os.getcwd(), 'summary results', "Digital returns summary run " +
                                                    current_run + ".csv"))

            overall_dig_returns = cumulative_dig_returns.sum(axis=0)
            average_dig_returns = (overall_dig_returns / hh_totals)*100
            average_dig_returns = pd.DataFrame(average_dig_returns).T
            average_dig_returns.to_csv(os.path.join(os.getcwd(), 'summary results', "Average digital returns run " +
                                                    current_run + ".csv"))

        except ValueError as e:
            print(e, " in run: ", current_run)

        try:

            # produce summary of paper returns
            cumulative_pap_returns = post_process.cumulative_sum(pandas_data['Return_sent'][str(current_run)], 0, 1824,
                                                                 24, geog, 'paper')
            hh_count.index = cumulative_pap_returns.index
            pap_returns_summary = cumulative_pap_returns.div(hh_count, axis='index')
            pap_returns_summary.to_csv(os.path.join(os.getcwd(), 'summary results', "Paper returns summary run " +
                                                    current_run + ".csv"))

            overall_pap_returns = cumulative_pap_returns.sum(axis=0)
            average_pap_returns = (overall_pap_returns / hh_totals)*100
            average_pap_returns = pd.DataFrame(average_pap_returns).T
            average_pap_returns.to_csv(os.path.join(os.getcwd(), 'summary results', "Average paper returns run " +
                                                    current_run + ".csv"))

        # if something goes wrong exit with error
        except ValueError as e:
            print(e, " in run: ", current_run)

    # do we always want to select this data frame - yes for the default output
    default_run = '1'
    df1 = pandas_data['Return_sent'][default_run]
    df2 = pandas_data['hh_record'][default_run]
    start_date = pandas_data['key info'][default_run].start_date[0]
    start_date = dt.date(*map(int, start_date.split('-')))
    post_process.produce_return_charts(df1, df2, 'Active', 'Passive', start_date, ' returns run 1.html')

    # example of how to produce a second chart based on next run - can also be used as second strategy in waterfall
    # df3 = pandas_data['Return_sent']['2']
    # df4 = pandas_data['hh_record']['2']
    # post_process.produce_return_charts(df3, df4, '  returns run 2.html')

    post_process.waterfall([df2, df2, 'passive', True], [df1, df2, 'active', False], bins=[65, 105, 5])


if __name__ == '__main__':

    create_new_config = False
    produce_default = False
    multiple_processors = False
    freeze_support()

    # delete all old output files from default location except generated JSON files.
    if os.path.isdir('outputs/'):
        dirs = [x[0] for x in os.walk('outputs/')]
        for d in dirs:
            if d != 'outputs/':
                shutil.rmtree(str(d))

    # read in input configuration file using a default if nothing is selected
    input_path = input('Enter input file path or press enter to use defaults: ')
    if len(input_path) < 1:
        file_name = 'inputs/CCA_small.JSON'

        input_path = os.path.join(os.getcwd(), file_name)

    try:
        with open(input_path) as data_file:
            input_data = json.load(data_file)

    # if something goes wrong exit with error
    except IOError as e:
        print(e)
        sys.exit()

    # ask for output destination or use a default if none specified
    output_path = input('Enter output path or press enter to use default: ')
    if len(output_path) < 1:
        outputs = 'outputs'
        output_path = os.path.join(os.getcwd(), outputs)

    try:
        if not os.path.isdir(output_path):
            os.makedirs(output_path)

    # if something goes wrong exit with error
    except IOError as e:
        print(e)
        sys.exit()

    # create a list of runs from configuration file
    list_of_runs = sorted(list(input_data.keys()), key=int)
    # define a list to be used to map all run/replication combinations to available processors
    run_list = []
    seed_dict = {}
    seed_list = []

    # place, with random seeds, a copy of the run/rep into the run list
    for run in list_of_runs:
        input_data[run]['run id'] = run
        seed_dict[str(run)] = {}
        for rep in range(1, input_data[run]['replications'] + 1):

            if str(rep) not in input_data[run]['replication seeds']:
                now = dt.datetime.now()
                seed_date = dt.datetime(2012, 4, 12, 19, 00, 00)
                seed = abs(now - seed_date).total_seconds() + int(run) + rep
                seed_dict[str(input_data[run]['run id'])][str(rep)] = seed
                create_new_config = True

            else:
                seed = input_data[run]['replication seeds'][str(rep)]

            seed_list.append(seed)

            input_data[run]['rep id'] = rep
            run_list.append(copy.deepcopy(input_data[run]))

    ts = time.time()
    st = dt.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    print(st)

    # different run methods - use single processor for debugging
    if multiple_processors:
        pool = Pool(cpu_count())  # use the next two lines to use multiple processors
        Pool().starmap(start_run, zip(run_list, seed_list, repeat(output_path)))
    else:
        for i in range(len(run_list)):
            start_run(run_list[i], seed_list[i], output_path)

    # at the end add the seed list and print out the JSON?
    if create_new_config:

        list_of_seed_runs = sorted(list(seed_dict.keys()), key=int)
        # first assign the seeds...
        for run in list_of_seed_runs:
            input_data[run]['replication seeds'] = seed_dict[run]
            # delete ids
            del input_data[run]['run id']
            del input_data[run]['rep id']

        output_JSON_name = str(dt.datetime.now().strftime("%Y""-""%m""-""%d %H.%M.%S")) + '.JSON'
        with open(os.path.join(output_path, output_JSON_name), 'w') as outfile:
            json.dump(input_data, outfile)

    if produce_default:
        produce_default_output()

    ts = time.time()
    st = dt.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    print(st)
