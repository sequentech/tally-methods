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
import math
from operator import itemgetter
from collections import defaultdict

from ..ballot_counter.ballots import Ballots
from ..ballot_counter.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException

# Desborda 3 is a modification/generalization of desborda 2.
# Basically, it's like Desborda 2, but without minorities corrections.

class Desborda3(BaseVotingSystem):
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
        return 'desborda3'

    @staticmethod
    def get_description():
        return _('Desborda 3 Count voting')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return Desborda3Tally(election, question_num)

class Desborda3Tally(BaseTally):
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

    method_name = "Desborda3"

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

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        answers = copy.deepcopy(voter_answers[self.question_num]['choices'])
        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return
        key_answers = str(answers)

        # don't count blank/invalid votes
        if len(answers) > 0:
            # if ballot found, increment the count. Else, create a ballot and add it
            if key_answers in self.ballots:
                self.ballots[key_answers]['votes'] += 1
            else:
                self.ballots[key_answers] = dict(votes=1, answers=answers)

    def desborda_tally(self, question, ballots):
        voters_by_position = [0] * question['max']
        for answer in question['answers']:
            answer['voters_by_position'] = copy.deepcopy(voters_by_position)
            answer['total_count'] = 0
            answer['winner_position'] = None

        # fill the 'voters_by_position' field on each answer
        for ballot_name, ballot in ballots.items():
            question['totals']['valid_votes'] += ballot['votes']
            for index, option in enumerate(ballot['answers']):
                question['answers'][option]['voters_by_position'][index] += ballot['votes']

        # if N is the number of winners, then the points start is
        # max_points = floor(N + 3N/10)
        max_points = int(math.floor(question['num_winners'] + 3*question['num_winners']/10))
        # do the total count, assigning max_points, max_points-1, max_points-2... points for each vote
        # on each answer depending on the position of the vote
        for answer in question['answers']:
            for index, num_voters in enumerate(answer['voters_by_position']):
                answer['total_count'] += max(1, max_points-index) * num_voters

        # first order by the name of the eligible answers
        sorted_by_text = sorted(
            question['answers'],
            key = lambda x: x['text'])

        # then order in reverse by the total count
        sorted_winners = sorted(
            sorted_by_text,
            key = lambda x: x['total_count'],
            reverse = True)

        for winner_pos, winner in enumerate(sorted_winners):
            winner['winner_position'] = winner_pos

    def perform_tally(self, questions):
        self.report = {}
        report = self.report
        question = questions[self.question_num]
        self.desborda_tally(question, self.ballots)

    def post_tally(self, questions):
        '''
        '''
        self.perform_tally(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report
