
import simpy
from simpy.util import start_delayed
import census
import household
import datetime
import math
import random


class Run(object):
    """contains the methods and data for an individual run"""

    def __init__(self, env, input_data, output_data, raw_output, rnd, run, reps, seed, error_log):

        self.env = env
        self.input_data = input_data
        self.output_data = output_data
        self.raw_output = raw_output
        self.rnd = rnd
        self.run = run
        self.reps = reps
        self.seed = seed
        self.error_log = error_log

        self.start_date = datetime.datetime.strptime(input_data['start_date'], '%Y, %m, %d, %H, %M, %S')
        self.end_date = datetime.datetime.strptime(input_data['end_date'], '%Y, %m, %d, %H, %M, %S')
        self.sim_hours = (self.end_date.date() - self.start_date.date()).total_seconds()/3600
        self.initial_hh_sep = 0  # initial average hh separation - does not change once set
        self.travel_time = 0  # changes based on number of households who have responded
        self.total_responses = 0  # simply tally of total responses
        self.fu_start = 0  # variable created ready to store time of FU
        self.total_enu_instances = 0
        self.total_ad_instances = 0
        self.total_ad_chat_instances = 0
        self.pq_sent = 0  # a flag to record if a pq was sent as a letter

        # temp only for simple output spreadsheet
        self.letter_sent = 0
        self.letter_effect = 0

        self.district = []  # a list of households in the district
        self.hh_count = {}  # simple dict containing a count of the hh types in the sim
        self.hh_resp = {}  # a simple dict to keep a tally of the hh who have responded
        self.list_of_hh = sorted(list(self.input_data['households']))  # top level keys only, hh in this case
        for hh in self.list_of_hh:
            self.hh_count[hh] = self.input_data['households'][hh]['number']

        '''below is for temp output only'''
        ################################################################################

        self.total_dig_resp = {}
        self.total_pap_resp = {}
        self.visit_counter = {}
        self.call_counter = {}
        self.visit_unnecessary_counter = {}
        self.visit_wasted_counter = {}
        self.visit_out_counter = {}
        self.visit_success_counter = {}
        self.visit_contact_counter = {}
        self.visit_assist_counter = {}
        self.visit_paper_counter = {}
        self.letter_sent_counter = {}
        self.letter_wasted_counter = {}
        self.letter_received_counter = {}
        self.letter_response_counter = {}
        self.phone_response_counter = {}
        self.pq_sent_counter = {}

        #################################################################################

        self.total_travel_dist = 0
        self.total_travel_time = 0
        self.enu_avail = []  # list use to hold enumerators instances when available for work
        self.enu_working = []  # list to store instances of working enumerators
        self.ad_avail = []
        self.ad_working = []
        self.ad_chat_avail = []
        self.ad_chat_working = []
        self.incomplete = []  # a list containing the households who submitted incomplete responses
        self.visit_list = []

        # below can be used turn functionality off regardless of contents of configuration file
        self.FU_on = True
        #self.call_FU_on = False
        self.advisers_on = False
        self.letters_on = True

        self.create_households(self.input_data['households'])

        if self.FU_on is True:
            self.start_coordinator(self.calc_fu_start(self.input_data['households']))  # places events in event list to enable coordinator to update visits list
            self.create_enumerators(self.input_data["collector"], self.start_date)

        if self.advisers_on is True:
            self.create_advisers(self.input_data["advisers"], "")

        # create required stores but only if there are resources to put inside them
        if self.total_ad_instances > 0:
            self.adviser_store = simpy.FilterStore(self.env, capacity=self.total_ad_instances)
        if self.total_ad_chat_instances > 0:
            self.adviser_chat_store = simpy.FilterStore(self.env, capacity=self.total_ad_chat_instances)

        if self.letters_on is True:
            self.start_letters(self.input_data["households"])

        # and create some some simple (and temp) output
       # self.resp_day(744)
        self.resp_day(self.sim_hours)

    """creates the households and calculates the initial hh separation"""
    def create_households(self, input_dict):

        id_num = 0

        # dicts are unsorted so hh will not always be created in the same order as defined
        # this could impact on visit order so the list is shuffled after creation

        for hh_type, value in input_dict.items():

            for i in range(input_dict[hh_type]['number']):

                self.district.append(household.Household(self, self.env, hh_type, id_num, input_dict[hh_type]))
                id_num += 1

        # shuffle the list - so if pri equal the order of visits is random
        random.shuffle(self.district)

        # then define for the run the initial distance between houses
        hh_area = self.input_data['district_area'] / len(self.district)
        self.initial_hh_sep = 2*(math.sqrt(hh_area/math.pi))

    """set in hours when the earliest fu start time based on input dates"""
    def calc_fu_start(self, input_data):

        output_value = 0

        for key, value in input_data.items():
            if isinstance(value, dict):

                output_value = self.calc_fu_start(value)
            elif key == "FU_start_time":
                if self.fu_start == 0 or value < self.fu_start:
                    return value

        return output_value

    """Starts the coordinator who updates the visit list starting at the set FU time"""
    def start_coordinator(self, fu_start):
        start_delayed(self.env, census.fu_startup(self, self.env, self.district, self.input_data['coordinator_update']),
                      fu_start)

    """create instances of an enumerators"""
    def create_enumerators(self, input_data, input_key):

        id_num = self.total_enu_instances
        for key, value in input_data.items():
            if isinstance(value, dict):

                self.create_enumerators(value, key)
            elif key == "number":

                for i in range(int(input_data["number"])):

                    self.enu_avail.append(census.Enumerator(self,
                                                            id_num,
                                                            input_data['start_time'],
                                                            input_data['end_time'],
                                                            input_data['start_date'],
                                                            input_data['end_date'],
                                                            input_key,
                                                            input_data['travel_speed'],
                                                            self.input_data['households'],  # households to visit
                                                            self.FU_on))
                    id_num += 1
                    self.total_enu_instances += 1

        return input_key

    def create_advisers(self, input_data, input_key):

        # create the advisers - different types
        id_ad_num = self.total_ad_instances
        id_ad_chat_num = self.total_ad_instances
        for key, value in input_data.items():
            if isinstance(value, dict):

                self.create_advisers(value, key)
            elif key == "number" and ("telephone" in input_key) == True:
                for i in range(int(input_data["number"])):

                    self.ad_avail.append(census.Adviser(self,
                                                        id_ad_num,
                                                        input_data["start_time"],
                                                        input_data["end_time"],
                                                        input_data["start_date"],
                                                        input_data["end_date"],
                                                        input_key,
                                                        input_data["FU_on"]))
                    id_ad_num += 1
                    self.total_ad_instances += 1

            elif key == "number" and ("web" in input_key) == True:
                for i in range(int(input_data["number"])):

                    self.ad_chat_avail.append(census.AdviserChat(self,
                                                                 id_ad_chat_num,
                                                                 input_data["start_time"],
                                                                 input_data["end_time"],
                                                                 input_data["start_date"],
                                                                 input_data["end_date"],
                                                                 input_key))
                    id_ad_chat_num += 1
                    self.total_ad_chat_instances += 1


        return input_key

    """scheduling of events to start the posting of letters at defined times"""
    def start_letters(self, input_dict):

        # input dict is the entire hh section of current run
        list_of_hh = sorted(list(input_dict.keys()))  # top level keys only, hh in this case

        for hh in list_of_hh:

            letter_phases = input_dict[hh]["letter_phases"]  # dict of just the letters for that hh

            list_of_letters = sorted(list(letter_phases.keys()))  # top level keys only
            if len(list_of_letters) != 0:

                for letter in list_of_letters:
                    letter_date = datetime.datetime.strptime(letter_phases[letter]["date"], '%Y, %m, %d, %H, %M, %S')
                    self.letter_sent = (letter_date - self.start_date).total_seconds()/3600  # for waves for temp output make a list??

                    # below only applicable if only 1 letter sent- for simple output only - delete in long term

                    self.letter_effect = letter_phases[letter]["effect"]  # for waves for temp output make a list??

                    if self.letter_sent != 0:
                        start_delayed(self.env, census.letter_startup(self,
                                                                      self.env,
                                                                      self.district,
                                                                      self.output_data,
                                                                      self.sim_hours,
                                                                      letter_phases[letter],
                                                                      letter,
                                                                      hh),
                                      self.letter_sent)
                    else:
                        self.env.process(census.letter_startup(self,
                                                               self.env,
                                                               self.district,
                                                               self.output_data,
                                                               self.sim_hours,
                                                               letter_phases[letter],
                                                               letter,
                                                               hh))

    def resp_day(self, delay):

        start_delayed(self.env, census.print_resp(self), delay - 24)


def str2bool(value):
    return str(value).lower() in ("True", "true", "1")





