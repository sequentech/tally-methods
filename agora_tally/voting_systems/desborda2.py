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

# Desborda 2 is a modification/generalization of desborda. 
# Desborda is defined here:
# http://pabloechenique.info/wp-content/uploads/2016/12/DesBorda-sistema-Echenique.pdf

# If N is the number of winners, then the maximum points for a candidate per
# ballot will be:

# MAXP=floor(1.3*N)

# If M is the maximum number of candidates a voter can include in a ballot,
# the points that the ballot adds to each candidate will be:

# POINTS=max(1, MAXP - order)

# where 'order' is the preferential order of the candidate in the ballot (for
# example 0 for the first option, and M-1 for the last one).

# The number of female winners can be greater than the number of male winners,
# but if the number of male winners is greater than the female ones, a zipped
# parity algorithm will be applied.

# When the number of winners is more than 29, if a group of candidates has
# more than 5% of all the points, the group will be guaranteed 1 winner
# position. Also in this case, if a group has more than 10% of all the
# points, it will be guaranteed 2 winner positions. Also in this case, if a
# group has more than 15% of all the points, it will be guaranteed 3 winner
# positions. If 2 or 3 candidates win by this mechanism, the maximum number of
# male winners in each case will be one.

# When the number of winners is less or equal than 29, if a group of
# candidates has more than 10% of all the points, the group will be guaranteed 1 winner
# position. Also in this case, if a group has more than 20% of all the
# points, it will be guaranteed 2 winner positions. If 2 candidates win 
# by this mechanism, the maximum number of male winners in each case will be
# one.

class Desborda2(BaseVotingSystem):
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
        return 'desborda2'

    @staticmethod
    def get_description():
        return _('Desborda 2 Count voting')

    @staticmethod
    def create_tally(question, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return Desborda2Tally(question=question, question_num=question_num)

class Desborda2Tally(BaseTally):
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

    method_name = "Desborda2"

    # report object
    report = None

    def init(self):
        self.ballots = dict()

        def custom_subparser(decoded_ballot, _question, withdrawals):
            sorted_ballot_answers = copy.deepcopy(decoded_ballot['answers'])
            sorted_ballot_answers.sort(key=itemgetter('selected'))
            return [
                answer['id']
                for answer in sorted_ballot_answers
                if answer['selected'] > -1 and answer['id'] not in withdrawals
            ]
        self.custom_subparser = custom_subparser

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
        #
        # NOTE: Using here 'max' instead of 'num_winners' as requested in
        # https://gitlab.nvotes.com/nvotes/pode-22/issues/15
        if 'bordas-max-points' not in question:
            base_max_points = question['max']
        else:
            base_max_points = question['bordas-max-points']

        max_points = int(math.floor(base_max_points + 3*base_max_points/10))

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
