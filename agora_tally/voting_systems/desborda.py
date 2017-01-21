# This file is part of agora-tally.
# Copyright (C) 2017  Agora Voting SL <agora@agoravoting.com>

# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import random
import copy
import uuid
import sys
import codecs
import os
from operator import itemgetter
from collections import defaultdict

from ..ballot_counter.ballots import Ballots
from ..ballot_counter.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException

# Definition of this system: 
# http://pabloechenique.info/wp-content/uploads/2016/12/DesBorda-sistema-Echenique.pdf
#
# Description:
# It's a modification of the Borda Count https://en.wikipedia.org/wiki/Borda_count
# It's a multiple winner election method in which voters rank candidates in order of preference.
# There will be 62 winners.
# Although each voter can create their ballot choosing the individual candidates,
# candidates are grouped into teams.
# Each team consists of 20 to 62 candidates, and they are presented in order, 
# although the voter can of course alter the order however he wants.
# Candidates can be either male or female. The first candidate of each team is
# a female and males and females are presented in a zipped way (f,m,f,m...)
# Each ballot can contain up to 62 candidates.
# On each ballot, the first candidate gets 80 points, and the last one 20.
# A second round can be done after correcting the minorities from the first  round.
# On the first round, teams that get more than 5% of all points and less than 2
# candidates elected will get their two most voted candidates  (female and male)
# elected.
# Also on the first round, teams that get more than 15% of the votes and less
# than 4 candidates elected, will get their 4 most voted candidates (2 females
# and 2 males).
# If there have been minorities corrections on the first round, there will be a
# second round. On the second round, the number of seats will be 62 minus the
# number of seats given to the minorities by the corrections.
# Likewise, on this second round all candidates from all teams that got seats on
# the first round because of the corrections will be withdrawn from all ballots
# on the second round. This means that if a ballot on the first round is:
# A1 (80 points), B6 (79 points), A2 (78 points)...
# and team B got elected B1 and B2 (but not B6, for example) on the first round
# because of a minorities correction, then on the second round this ballot
# would be:
# A1 (80 points), A2 (79 points)...
# because all candidates from team B are withdrawn for the second round, even
# those that didn't get elected.
# On this second round, or on the first if there are no minorities corrections,
# if there are more male winners than female winners then the zip correction
# will be applied so that there is as many female as male winners, starting with
# a female.

class Desborda(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage an OpenSTV-based
     Borda voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'desborda'

    @staticmethod
    def get_description():
        return _('Desborda Count voting')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return DesbordaTally(election, question_num)

class DesbordaTally(BaseTally):
    '''
    Class used to tally an election
    '''
    ballots_file = None
    ballots_path = ""

    # dict containing the current list of ballots.
    # each dict key is the str of the choices, so if the choices are [2, 1, 4]
    # then the dict key of those ballots is '[2, 1, 4]'
    # In each iteration this list is modified. For efficiency, ballots with the
    # same ordered choices are grouped. The format of each item in this list is
    # the following:
    #
    #'[2, 1, 4]': {
    #    'votes': 12, # number of ballots with this selection of choices
    #    'answers': [2, 1, 4] # list of ids of the choices
    #}
    ballots = dict()

    num_winners = -1

    method_name = "Desborda"

    # report object
    report = None

    def init(self):
        self.ballots = dict()

    def parse_vote(self, number, question, withdrawals=[]):
        vote_str = str(number)
        tab_size = len(str(len(question['answers']) + 2))

        # fix add zeros
        if len(vote_str) % tab_size != 0:
            num_zeros = (tab_size - (len(vote_str) % tab_size)) % tab_size
            vote_str = "0" * num_zeros + vote_str

        ret = []
        for i in range(int(len(vote_str) / tab_size)):
            option = int(vote_str[i*tab_size: (i+1)*tab_size]) - 1

            if option in withdrawals:
                continue
            # blank vote
            elif option == len(question['answers']) + 1:
                raise BlankVoteException()
            # invalid vote
            elif option < 0 or option >= len(question['answers']):
                raise Exception()
            ret.append(option)

        # detect invalid vote
        if len(ret) < question['min'] or len(set(ret)) != len(ret):
            raise Exception()
        if len(ret) > question['max']:
            if "truncate-max-overload" in question and question["truncate-max-overload"]:
                ret = ret[:question['max']]
            else:
                raise Exception()

        return ret

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        import codecs
        import os
        if not os.path.exists(os.path.dirname(self.ballots_path)):
            os.makedirs(os.path.dirname(self.ballots_path))

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        answers = [choice for choice in voter_answers[self.question_num]['choices']]
        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return
        key_answers = str(answers)

        # if ballot found, increment the count. Else, create a ballot and add it
        if key_answers in self.ballots:
            self.ballots[key_answers]['votes'] += 1
        else:
            self.ballots[key_answers] = dict(votes=1, answers=answers)

    def borda_tally(question, ballots):
        question['answers'].sort(key = lamda x: x['id'])
        voters_by_position = [0] * question['max']
        for answer in question['answers']:
            answer['voters_by_position'] = copy.deepcopy(voters_by_position)
        pass

    def perform_tally(self, questions):
        self.report = {}
        report = self.report
        question = questions[self.question_num]
        round1 = borda_tally(question, self.ballots)

    def post_tally(self, questions):
        '''
        '''
        self.perform_tally(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report.json
