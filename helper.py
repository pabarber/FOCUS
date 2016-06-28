"""module containing functions used across modules"""
import datetime as dt


def returns_to_date(district, output_format=""):

    count = len([hh.id for hh in district.households if hh.resp_rec is True])

    if output_format == "%":

        return count/len(district.households)

    else:
        return (count/len(district.households))*100


def current_day(obj):

    current_date_time = obj.rep.start_date + dt.timedelta(hours=obj.rep.env.now)
    current_date = current_date_time.date()
    day = current_date.weekday()

    return day


def simpy_to_time(simpy_time):

    days = int(simpy_time/24)
    hours = int(simpy_time - days*24)
    mins = ((simpy_time - days*24) - hours)*60
    secs = int((mins - int(mins))*60)

    time = str(hours) + "," + str(int(mins)) + "," + str(secs)

    return dt.datetime.strptime(time, '%H,%M,%S').time()


def make_time(hours, mins, secs):

    time = str(hours) + "," + str(mins) + "," + str(secs)

    return dt.datetime.strptime(time, '%H,%M,%S').time()


def make_time_decimal(time_object):

    hours = time_object.hour
    mins = time_object.minute
    secs = time_object.second

    return hours + mins/60 + secs/3600


def return_time_key(input_dict, time):

    time = make_time_decimal(simpy_to_time(time))

    key_list = sorted(list(input_dict.keys()), key=int)

    for key in key_list:
        if int(key) >= time:
            return key
