"""Class used to represent area coordinators. 1 per area so FU can start at different times
for different areas if need be. Not needed to run multiple simulations if districts do not
interact. But useful if districts are needed to interact"""
from collections import namedtuple
import datetime
import math
import csv
from simpy.util import start_delayed
import logging


FU_start = namedtuple('FU_start', ['Time'])
letter_sent = namedtuple('letter_sent', ['run', 'reps', 'Time', 'Household',  'hh_type', 'Type'])
visit = namedtuple('Visit', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_out = namedtuple('Visit_out', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_contact = namedtuple('Visit_contact', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_wasted = namedtuple('Visit_wasted', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_unnecessary = namedtuple('Visit_unnecessary', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_success = namedtuple('Visit_success', ['run', 'reps', 'Time', 'Household', 'Type'])
enu_util = namedtuple('Enu_util', ['run', 'reps', 'Time', 'Count'])  # enumerator usage over time
enu_travel = namedtuple('Enu_travel', ['run', 'reps', 'Enu_id', 'Time', 'Distance', 'Travel_time'])
visit_assist = namedtuple('Visit_assist', ['run', 'reps', 'Time', 'Household', 'Type'])
visit_paper = namedtuple('Visit_paper', ['run', 'reps', 'Time', 'Household', 'Type'])
partial_response_times = namedtuple('Partial_response', ['run', 'reps', 'Time', 'Household'])  # time partial response received


def print_resp(run):
    """returns the responses received to date for the current run and other counters"""

    # populate the simple dicts for the totals
    for hh in run.list_of_hh:
            run.hh_resp[hh] = 0
            run.total_dig_resp[hh] = 0
            run.total_pap_resp[hh] = 0
            run.visit_counter[hh] = 0
            run.call_counter[hh] = 0
            run.visit_unnecessary_counter[hh] = 0
            run.visit_wasted_counter[hh] = 0
            run.visit_out_counter[hh] = 0
            run.visit_success_counter[hh] = 0
            run.visit_contact_counter[hh] = 0
            run.visit_assist_counter[hh] = 0
            run.visit_paper_counter[hh] = 0
            run.letter_sent_counter[hh] = 0
            run.letter_wasted_counter[hh] = 0
            run.letter_received_counter[hh] = 0
            run.letter_response_counter[hh] = 0
            run.phone_response_counter[hh] = 0
            run.pq_sent_counter[hh] = 0

    for item in run.output_data:
        if type(item).__name__ == 'Responded' and item[0] == run.run and item[1] == run.reps:
            run.hh_resp[item[4]] += 1
            if item[7] == 'digital':
                run.total_dig_resp[item[4]] += 1
            elif item[7] == 'paper':
                run.total_pap_resp[item[4]] += 1
        elif type(item).__name__ == 'Visit' and item[0] == run.run and item[1] == run.reps:
            run.visit_counter[item[4]] += 1
        elif type(item).__name__ == 'Phone_call' and item[0] == run.run and item[1] == run.reps:
            run.call_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_unnecessary' and item[0] == run.run and item[1] == run.reps:
            run.visit_unnecessary_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_wasted' and item[0] == run.run and item[1] == run.reps:
            run.visit_wasted_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_out' and item[0] == run.run and item[1] == run.reps:
            run.visit_out_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_success' and item[0] == run.run and item[1] == run.reps:
            run.visit_success_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_contact' and item[0] == run.run and item[1] == run.reps:
            run.visit_contact_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_assist' and item[0] == run.run and item[1] == run.reps:
            run.visit_assist_counter[item[4]] += 1
        elif type(item).__name__ == 'Visit_paper' and item[0] == run.run and item[1] == run.reps:
            run.visit_paper_counter[item[4]] += 1
        elif type(item).__name__ == 'letter_sent' and item[0] == run.run and item[1] == run.reps:
            run.letter_sent_counter[item[4]] += 1
        elif type(item).__name__ == 'letter_wasted' and item[0] == run.run and item[1] == run.reps:
            run.letter_wasted_counter[item[4]] += 1
        elif type(item).__name__ == 'letter_received' and item[0] == run.run and item[1] == run.reps:
            run.letter_received_counter[item[4]] += 1
        elif type(item).__name__ == 'letter_response' and item[0] == run.run and item[1] == run.reps:
            run.letter_response_counter[item[4]] += 1
        elif type(item).__name__ == 'phone_response' and item[0] == run.run and item[1] == run.reps:
            run.phone_response_counter[item[4]] += 1
        elif type(item).__name__ == 'pq_received' and item[0] == run.run and item[1] == run.reps:
            run.pq_sent_counter[item[4]] += 1

    print(run.run, run.reps)


    for key, value in sorted(run.hh_resp.items()):  # sort the dictionary for output purposes
        print(key, value/run.hh_count[key])

    for key, value in sorted(run.hh_resp.items()):
        try:
            data = [run.run,
                    run.reps,
                    (run.input_data['households'][key]['number']),
                    key,
                    (run.input_data['district_area']),
                    (run.input_data['households'][key]['allow_paper']),
                    (run.input_data['households'][key]['paper_after_max_visits']),
                    run.pq_sent,  # simple flag to mark if pq sent as letter
                    (run.input_data['households'][key]['FU_on']),
                    (run.input_data['households'][key]['default_resp']),
                    (run.input_data['households'][key]['paper_prop']),
                    (run.input_data['households'][key]['FU_start_time']),
                    (run.input_data['households'][key]['dig_assist_eff']),
                    (run.input_data['households'][key]['dig_assist_flex']),
                    (run.input_data['households'][key]['max_visits']),
                    (run.input_data['households'][key]['contact_rate']),
                    (run.input_data['households'][key]['conversion_rate']),
                    (run.input_data['households'][key]['call_conversion_rate']),
                    run.total_enu_instances,  # all types
                    run.total_ad_instances,  # all types
                    run.letter_sent,  # time letters sent
                    run.letter_effect,  # change this to reflect letter effect???
                    # outputs from here
                    value,
                    run.total_dig_resp[key],
                    run.total_pap_resp[key],
                    run.visit_counter[key],
                    run.visit_unnecessary_counter[key],
                    run.visit_wasted_counter[key],
                    run.visit_out_counter[key],
                    run.visit_success_counter[key],
                    run.visit_contact_counter[key],
                    run.visit_assist_counter[key],
                    run.visit_paper_counter[key],
                    run.call_counter[key],
                    run.phone_response_counter[key],
                    run.letter_wasted_counter[key],
                    run.letter_received_counter[key],
                    run.letter_response_counter[key],
                    run.pq_sent_counter[key],
                    run.total_travel_dist,
                    run.total_travel_time,
                    run.seed]

            # add code to print to a file instead/as well
            with open('outputs/' + run.raw_output, 'a', newline='') as csv_file:
                output_file = csv.writer(csv_file, delimiter=',')
                output_file.writerow(data)

        except:
            # skip any that cause errors -at some point add in what caused them!
            pass

    yield run.env.timeout(0)


# a helper process that creates an instance of a coordinator class and starts it working
def fu_startup(run, env, district, update_freq):

    Coordinator(run, env, district, update_freq)
    yield env.timeout(0)


# a helper process that creates an instance of a letter phase class
def letter_startup(run, env, district, output_data, sim_hours, input_data, letter_name, targets):

    LetterPhase(run, env, district, output_data, sim_hours, input_data, letter_name, targets)
    yield env.timeout(0)


# a simple event representing the response being received
def resp_rec(env, hh, run):

    call_response_test = run.rnd.uniform(0, 100)  # allow for a percentage of incomplete responses

    """but what percent by each group sends in incomplete responses?"""
    if call_response_test <= hh.input_data['send_incomplete']:
        hh.pri += 0  # allows for hh pri for FU to be changed if required - add to inputs
        hh.output_data.append(partial_response_times(run.run, run.reps, hh.resp_time, hh.id_num))
        """do these need to be followed up by a dedicated team or others? Add to a list for now"""
        run.incomplete.append(hh)

    else:

        hh.resp_rec = True
        run.total_responses += 1

    yield env.timeout(0)


class Coordinator(object):
    """represents the coordinator for the assigned district"""
    def __init__(self, run, env, district, update_freq):
        self.env = env
        self.run = run
        self.district = district
        self.check = env.process(self.arrange_visits())  # will start the action process
        self.update_freq = update_freq
        self.update_count = 0
        self.current_hh_sep = 0

    def arrange_visits(self):
        while True:

            self.run.visit_list = []

            for household in self.run.district:
                if household.resp_rec is False and household.fu_start <= self.env.now and household.FU_on is True and\
                                household.visits < household.max_visits:
                    self.run.visit_list.append(household)

            """sort what is left by pri - lower numbers first"""
            self.run.visit_list.sort(key=lambda hh: hh.pri, reverse=False)

            #print(len(self.run.visit_list), self.env.now)

            # re-calculate travel time based on households left to visit in area
            try:
                self.current_hh_sep = self.run.initial_hh_sep / (math.sqrt(1-(self.run.total_responses /
                                                                              len(self.run.district))))

            except ZeroDivisionError:

                logging.exception('Exception in run {0}, replication {1} at time {2} with seed {3}'
                                  .format(self.run.run, self.run.reps, self.env.now, self.run.seed))
                raise

            yield self.env.timeout(self.update_freq*24)  # effectively sorted at 00:00. What time would this happen?


class LetterPhase(object):
    def __init__(self, run, env, district, output_data, sim_hours, input_data, letter_name, targets):
        self.run = run
        self.env = env
        self.district = district
        self.output_data = output_data
        self.sim_hours = sim_hours
        self.targets = targets
        self.delay = input_data['delay']
        self.letter_type = letter_name
        self.effect = input_data['effect']
        self.targeted = str2bool(input_data["targeted"])
        self.pq = str2bool(input_data['pq'])

        env.process(self.fu_letter())

    def fu_letter(self):
        # need to add an option to send bulk letters rather than targeted
        # targeted is print on demand which costs more or takes longer??
        for household in self.district:
            if self.targeted is True and household.resp_rec is False and household.hh_type in self.targets:
                # send a letter
                self.env.process(self.co_send_letter(household, self.letter_type, self.effect, self.delay, self.pq))
            elif self.targeted is False and household.hh_type in self.targets:
                self.env.process(self.co_send_letter(household, self.letter_type, self.effect, self.delay, self.pq))
            # add an option to send to all ina group whether replied or not
                """what is the overhead, if any, of sending only to non responders?"""

        # then pause until the end
        yield self.env.timeout((self.sim_hours) - self.env.now)

    def co_send_letter(self, household, letter_type, effect, delay, pq):
        self.output_data.append(letter_sent(self.run.run, self.run.reps, self.env.now, household.id_num, household.hh_type, letter_type))
        # send a letter which will take an amount of time to be received (which could vary if required?)
        # then the hh needs to do something...at the right time
        start_delayed(self.env, household.rec_letter(letter_type, effect, pq), delay)
        yield self.env.timeout(0)


class Adviser(object):
    """Call centre adviser - multitasking"""

    def __init__(self, run, id_num, start_time, end_time, start_date, end_date, ad_type, do_fu_calls):

        self.env = run.env
        self.run = run
        self.id_num = id_num
        self.do_fu_calls = do_fu_calls
        self.start_time = start_time
        self.end_time = end_time
        self.start_date = datetime.datetime.strptime(start_date, '%Y, %m, %d')
        self.end_date = datetime.datetime.strptime(end_date, '%Y, %m, %d')
        self.ad_type = ad_type


        self.avail = False
        self.time_answered = 0
        self.length_of_call = 0
        self.current_hh = 0

        # add a process that adds the adviser to the store at the passed time
        # and removes later and so on until the end of the sim
        # while out of the store place in a storage list/store?
        # test how quick this turns out to be???
        temp_switch = 1
        if temp_switch == 1:
            # do the new stuff
            self.run.env.process(self.set_availability())  # starts the process which runs the visits

        if str2bool(self.do_fu_calls) is True:
            # add a switch to turn this on or off
            run.env.process(self.fu_call())  # starts the process which runs the vi

    def set_availability(self):

        start_delay = self.start_time + (self.start_date - self.run.start_date).total_seconds()/3600
        end_delay = self.end_time + (self.start_date - self.run.start_date).total_seconds()/3600
        repeat = (self.end_date - self.start_date).days + 1

        for i in range(repeat):

            start_delayed(self.run.env, self.add_to_store(), start_delay)
            start_delayed(self.run.env, self.remove_from_store(), end_delay)
            start_delay += 24
            end_delay += 24

        yield self.run.env.timeout(0)

    def add_to_store(self):

        self.run.ad_avail.remove(self)
        self.run.adviser_store.put(self)
        yield self.run.env.timeout(0)

    def remove_from_store(self):


        # note potential pitfall here - adviser object may be in use by a hh when it is due to become unavailable.
        # Does this even still happen in this case? If yes when?
        # alternative may be to let a hh take a adviser and check at that point if it should still be available
        # if not remove it and let the hh grab another adviser???

        current_ad = yield self.run.adviser_store.get(lambda item: item.id_num == self.id_num)
        self.run.ad_avail.append(current_ad)
        yield self.run.env.timeout(0)

    def fu_call(self):

        while True:

            # if past start of FU
            if self.env.now >= self.run.fu_start:

                # get the working times for the day for the adviser
                temp_date = str((self.run.start_date + datetime.timedelta(hours=self.env.now)).date())
                #self.time_start = int(self.run.adviser_dict[temp_date]['time'].split('-')[0])

                #self.time_end = int(self.run.adviser_dict[temp_date]['time'].split('-')[1])

                if self.time_start <= self.env.now % 24 < self.time_end and self.avail is True and len(self.district) != 0:
                    # working but check if taking a phone call
                    self.time_answered = self.env.now
                    if self in self.run.adviser_store.items and len(self.district) != 0:
                        # is not
                        # so remove from the store at this point
                        # and take a hh from the FU list
                        """ if live lists available check again here if hh has responded"""
                        current_hh = self.district.pop(0)
                        current_ad = yield self.run.adviser_store.get(lambda item: item.id_num == self.id_num)

                        """use visits contact rates below as we don't have any better at the moment.
                        But we do halve the success rate as people are less likely to respond in this manner"""
                        call_answered = False
                        if self.run.rnd.uniform(0, 100) <= int(self.run.visit_contact_rates_dict[current_hh.hh_type]):
                            call_answered = True
                        # equally likely to be in but half as effective at convincing to respond
                        call_response = False
                        if self.run.rnd.uniform(0, 100) <= int(self.run.visit_conversion_rates_dict[current_hh.hh_type])/2:
                            call_response = True

                        # add one to the number of calls received
                        current_hh.calls += 1

                        # check if answered and respond
                        if call_answered is True and call_response is True:
                            self.length_of_call = 0.2
                            yield self.env.timeout(self.length_of_call)
                            yield self.run.adviser_store.put(current_ad)
                            self.env.process(current_hh.respond(True, 0))
                        elif call_answered is True and call_response is False:
                            self.length_of_call = 0.2
                            yield self.env.timeout(self.length_of_call)
                            yield self.run.adviser_store.put(current_ad)
                            self.district.append(current_hh)
                            #current_hh.pri = 0
                            current_hh.resp_level = 10
                            current_hh.help_level = 5
                            current_hh.refuse_level = 1
                            self.env.process(current_hh.action())
                        # elif answered and hh already responded add wasted call
                        elif call_answered is True and current_hh.resp_sent is True:
                            self.length_of_call = 0.05
                            yield self.env.timeout(self.length_of_call)
                            yield self.run.adviser_store.put(current_ad)
                            """add event to capture wasted call"""
                        else:
                            self.length_of_call = 0.05
                            yield self.env.timeout(self.length_of_call)
                            yield self.run.adviser_store.put(current_ad)
                            #current_hh.pri = 0
                            self.district.append(current_hh)
                    else:
                        # is on a call so wait until that call is finished
                        yield self.env.timeout((self.time_answered + self.length_of_call) - self.env.now)
                else:
                    # not working yet - wait until they are - change until time next available
                    yield self.env.timeout(1)
            else:  # not yet at start of FU so wait until you are
                yield self.env.timeout(self.run.fu_start - self.env.now)

    def get_ad(self):

        current_ad = yield self.run.adviser_store.get()  # gets an adviser from the store...
        # but check it's the right one...if not put it back and get the next one
        #print(current_ad.id_num)
        if current_ad.id_num != self.id_num:
            yield self.run.adviser_store.put(current_ad)
            self.env.process(self.get_ad())
        else:
            return current_ad


class AdviserChat(object):
    """dedicated web chat adviser"""

    def __init__(self, run, id_num, start_time, end_time, start_date, end_date, ad_type):

        self.env = run.env
        self.run = run
        self.id_num = id_num
        self.start_time = start_time
        self.end_time = end_time
        self.start_date = datetime.datetime.strptime(start_date, '%Y, %m, %d').date()
        self.end_date = datetime.datetime.strptime(end_date, '%Y, %m, %d').date()
        self.ad_type = ad_type

        self.avail = False

        temp_switch = 1
        if temp_switch == 1:
            # do the new stuff
            self.run.env.process(self.set_availability())  # starts the process which runs the visits

    def set_availability(self):

        start_delay = self.start_time + 24*(self.start_date - self.run.start_date.date()).days
        end_delay = self.end_time + 24*(self.start_date - self.run.start_date.date()).days
        repeat = (self.end_date - self.start_date).days + 1

        for i in range(repeat):

            start_delayed(self.run.env, self.add_to_store(), start_delay)
            start_delayed(self.run.env, self.remove_from_store(), end_delay)
            start_delay += 24
            end_delay += 24

        yield self.run.env.timeout(0)

    def add_to_store(self):

        self.run.ad_chat_storage_list.remove(self)
        self.run.adviser_chat_store.put(self)
        yield self.run.env.timeout(0)

    def remove_from_store(self):

        # note potential pitfall here - adviser object may be in use by a hh when it is due to become available.
        # Does this even still happen in this case? If yes when?
        # alternative may be to let a hh take a adviser and check at that point if it should still be available
        # if not remove it and let the hh grab another adviser???

        current_ad = yield self.run.adviser_chat_store.get(lambda item: item.id_num == self.id_num)
        self.run.ad_chat_storage_list.append(current_ad)
        yield self.run.env.timeout(0)


class AdviserIncomplete(object):
    """dedicated adviser that FU incomplete responses"""

    def __init__(self, run):
        self.env = run.env
        self.run = run


class Enumerator(object):
    """represents an individual enumerator. Each instance can be different"""
    # need to add tracking to here....
    def __init__(self, run, id_num, start_time, end_time, start_date, end_date, enu_type, travel_speed, input_data,
                 visits_on):

        self.run = run
        self.id_num = id_num
        self.start_time = start_time
        self.end_time = end_time
        self.start_date = datetime.datetime.strptime(start_date, '%Y, %m, %d')
        self.end_date = datetime.datetime.strptime(end_date, '%Y, %m, %d')
        self.enu_type = enu_type
        self.travel_speed = travel_speed
        self.input_data = input_data
        self.visits_on = visits_on

        self.total_distance_travelled = 0
        self.distance_travelled = 0
        self.total_travel_time = 0
        self.travel_time = 0
        self.visits = 0

        #if self.visits_on is True:
        run.env.process(self.fu_visit_contact())  # starts the process which runs the visits

    def fu_visit_contact(self):
        """does the enumerator make contact with the hh"""

        while True:

            if self.working_test() is True and len(self.run.visit_list) != 0:

                self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))
                # transfer to working list
                self.run.enu_working.append(self)
                self.run.enu_avail.remove(self)
                self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))

                # visit
                current_hh = self.run.visit_list.pop(0)  # get next household to visit - and remove from master list

                """if hand helds available check if responded and if so do not visit -
                remove from list and move to next hh"""

                current_hh.visits += 1  # increase visits to that hh by 1
                current_hh.pri = current_hh.visits  # is this the right logic to prioritise visits?

                self.visits += 1

                try:
                    self.distance_travelled = self.run.initial_hh_sep / (math.sqrt(1 - (self.run.total_responses /
                                                                                        len(self.run.district))))
                    self.total_distance_travelled += self.distance_travelled

                    self.travel_time = self.distance_travelled / self.travel_speed
                    self.total_travel_time += self.travel_time

                except:
                    self.total_distance_travelled = 0
                    self.total_travel_time += 0

                self.run.output_data.append(enu_travel(self.run.run, self.run.reps, self.id_num, self.run.env.now,
                                                       self.total_distance_travelled, self.total_travel_time))

                ####### more temp output to calc total travel time and dist?

                self.run.total_travel_dist += self.distance_travelled
                self.run.total_travel_time += self.travel_time

                #######

                self.run.output_data.append(visit(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                  current_hh.hh_type))

                # visited but would have replied if not visited
                if current_hh.resp_planned is True and current_hh.resp_sent is False:
                    # add record of a visit that was not required but otherwise carry on
                    self.run.output_data.append(visit_unnecessary(self.run.run, self.run.reps, self.run.env.now,
                                                                  current_hh.id_num, current_hh.hh_type))
                if current_hh.resp_sent is True:
                    # add record of a visit that was not required but otherwise carry on
                    self.run.output_data.append(visit_wasted(self.run.run, self.run.reps, self.run.env.now,
                                                             current_hh.id_num, current_hh.hh_type))

                hh_in = False  # contact rate

                if self.run.rnd.uniform(0, 100) <= self.input_data[current_hh.hh_type]['contact_rate']:
                    hh_in = True
                    self.run.output_data.append(visit_contact(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                              current_hh.hh_type))

                if hh_in is True and (current_hh.resp_type == 'paper' and current_hh.paper_allowed is False):
                    yield self.run.env.process(self.fu_visit_assist(current_hh))
                elif hh_in is True and (current_hh.resp_type == 'digital' and current_hh.paper_allowed is False):
                    yield self.run.env.process(self.fu_visit_outcome(current_hh))
                elif hh_in is True and current_hh.paper_allowed is True:
                    yield self.run.env.process(self.fu_visit_outcome(current_hh))
                else:
                    # not in
                    self.run.output_data.append(visit_out(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                          current_hh.hh_type))

                    yield self.run.env.timeout((3 / 60) + self.travel_time)  # travel time spent
                    # will need to add back to the overall list with an update pri
                    # current_hh.pri += 0
                    # then put back in the list at the end if below max_visit number
                    if current_hh.visits < current_hh.max_visits:
                        self.run.visit_list.append(current_hh)
                    elif current_hh.paper_after_max_visits is True and current_hh.resp_type == 'paper':
                        '''add event to give paper if max visits received - but what will the HH then do?
                        a dig preference, who decided to do nothing  could get a paper copy here and the respond
                        is this sensible?'''
                        self.run.output_data.append(visit_paper(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                                current_hh.hh_type))
                        current_hh.paper_allowed = True
                        current_hh.resp_level = current_hh.decision_level(self.input_data[current_hh.hh_type], "resp")
                        current_hh.help_level = current_hh.resp_level + current_hh.decision_level(self.input_data[current_hh.hh_type], "help")

                        self.run.env.process(current_hh.action())

                    # transfer enumerator back to available list
                    self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))
                    self.run.enu_working.remove(self)
                    self.run.enu_avail.append(self)
                    self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))

            elif self.working_test() is False:
                    # not yet at work, time out until the next time they are due to start work
                yield self.run.env.timeout(self.hold_until())
            else:
                yield self.run.env.timeout(24)

    def fu_visit_assist(self, current_hh):
        """once contact is made determine if digital assistance is required"""

        if current_hh.resp_type == 'paper':
            dig_assist_test = self.run.rnd.uniform(0, 100)
            if dig_assist_test < current_hh.input_data['dig_assist_eff']:
                # persuades hh to switch to digital from paper
                current_hh.resp_type = 'digital'
                current_hh.delay = 0
                """how long would it take to change their minds?"""
                yield self.run.env.timeout(0.2 + self.travel_time)
                yield self.run.env.process(self.fu_visit_outcome(current_hh))

            elif current_hh.input_data['dig_assist_eff'] <= dig_assist_test <\
                    (current_hh.input_data['dig_assist_eff'] + current_hh.input_data['dig_assist_flex'])\
                    or (current_hh.visits == current_hh.max_visits and current_hh.paper_after_max_visits is True):
                # allows hh to use paper to respond
                """how long to get to the point of letting them have paper?"""
                yield self.run.env.timeout(0.2 + self.travel_time)
                self.run.output_data.append(visit_paper(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                        current_hh.hh_type))
                current_hh.paper_allowed = True
                current_hh.resp_level = current_hh.decision_level(self.input_data[current_hh.hh_type], "resp")
                current_hh.help_level = current_hh.resp_level + current_hh.decision_level(self.input_data[current_hh.hh_type], "help")

                yield self.run.env.process(self.fu_visit_outcome(current_hh))

            else:
                # suggests another form of digital assist...
                """how long would suggesting different forms of digital assist take?"""
                yield self.run.env.timeout(0.2 + self.travel_time)
                self.run.output_data.append(visit_assist(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num, current_hh.hh_type))
                # current_hh.pri = 0  # they have asked for help so raise the priority of the hh
                # so put hh back in the list to visit if max visits not reached
                if current_hh.visits < current_hh.max_visits:
                    self.run.visit_list.append(current_hh)
                # transfer enumerator back to available list
                self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))
                self.run.enu_working.remove(self)
                self.run.enu_avail.append(self)
                self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))

        else:
            yield self.run.env.process(self.fu_visit_outcome(current_hh))

    def fu_visit_outcome(self, current_hh):

        hh_responds = False

        if self.run.rnd.uniform(0, 100) <= self.input_data[current_hh.hh_type]['conversion_rate']:
            hh_responds = True

        # in but already replied
        if current_hh.resp_sent is True:
            self.run.output_data.append(visit_wasted(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num, current_hh.hh_type))
            yield self.run.env.timeout((5 / 60) + self.travel_time)

        # in and respond - there and then
        elif current_hh.resp_sent is False and hh_responds is True:
            self.run.output_data.append(visit_success(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                      current_hh.hh_type))
            current_hh.resp_planned = True
            yield self.run.env.timeout((30 / 60) + self.travel_time)
            self.run.env.process(current_hh.respond(current_hh.delay))

        # in but no immediate response
        elif current_hh.resp_sent is False and hh_responds is False:
            #self.run.output_data.append(visit_contact(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
             #                                         current_hh.hh_type))
            yield self.run.env.timeout((5 / 60) + self.travel_time)
            """After a visit where they don't respond what do hh then do?"""
            current_hh.resp_level = 0  # current_hh.decision_level(self.input_data[current_hh.hh_type], "resp")
            current_hh.help_level = 0  # current_hh.resp_level + current_hh.decision_level(self.input_data[current_hh.hh_type], "help")

            # current_hh.pri = 0
            # then put back in the list to visit at the end with new pri but only if below max_visit number
            if current_hh.visits < current_hh.max_visits:
                self.run.visit_list.append(current_hh)
            elif current_hh.paper_after_max_visits is True and current_hh.paper_allowed is False and current_hh.resp_type == 'paper':

                self.run.output_data.append(visit_paper(self.run.run, self.run.reps, self.run.env.now, current_hh.id_num,
                                                        current_hh.hh_type))
                current_hh.paper_allowed = True

            current_hh.status = "visited"

            self.run.env.process(current_hh.action())

        # transfer enumerator back to available list
        self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))
        self.run.enu_working.remove(self)
        self.run.enu_avail.append(self)
        self.run.output_data.append(enu_util(self.run.run, self.run.reps, self.run.env.now, len(self.run.enu_working)))

    def hold_until(self):

        if self.current_date() < self.start_date:
            diff = (self.start_date - self.current_date()).days * 24
            return diff + self.start_time
        elif self.current_date() >= self.start_date:
            if self.run.env.now % 24 < self.start_time:
                return self.start_time - self.run.env.now % 24
            elif self.run.env.now % 24 >= self.end_time:
                return self.start_time + (24 - self.run.env.now % 24)

    def current_date(self):
        return self.run.start_date + datetime.timedelta(hours=self.run.env.now)

    def working_test(self):
        """returns true or false to depending on whether or not an enumerator is available"""

        if (self.start_date <= self.current_date() <= self.end_date) \
                and (self.start_time <= self.run.env.now % 24 < self.end_time):
            return True
        else:
            #print(self.run.env.now, "F")
            return False


def str2bool(value):
    return str(value).lower() in ("True", "true", "1")











