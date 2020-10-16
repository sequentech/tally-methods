# This file is part of agora-tally.
# Copyright (C) 2019  Agora Voting SL <agora@agoravoting.com>

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
import itertools
from operator import itemgetter
from collections import defaultdict

from ..ballot_counter.ballots import Ballots
from ..ballot_counter.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException

# Definition of this system:
# Borda Count voting modified so that if you vote just a category in order,
# your ballot weights x5
#
# So for example if the options are:
# 1. Category1
# 1.1. Candidate1A
# 1.2. Candidate1B
# 2. Category2
# 2.1. Candidate2C
# 2.2. Candidate2D
#
# If a vote is [Candidate1A, Candidate2C] then Candidate1A gets +2 points,
# Candidate2C gets +1 point
#
# If a vote is [Candidate1A, Candidate1B] then Candidate1A gets +10 points,
# Candidate1B gets +5 points


class BordaMasMadrid(BaseVotingSystem):
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
        return 'borda-mas-madrid'

    @staticmethod
    def get_description():
        return _('Borda Count voting modified so that if you vote just ' +
                 'a category in order, your ballot weights x5')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BordaMasMadridTally(election, question_num)

class BordaMasMadridTally(BaseTally):
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
    #    'answers': [2, 1, 4], # list of ids of the choices
    #    'is_block_category_ballot': False # if this ballot represents a category
    #    # ballot, which means that it is the list of candidates of a category
    #    # in order and only that. These candidates will get a x5 boost
    #}
    ballots = dict()

    # Indicates how many times a ballot vote is worth if the vote is to a single
    # category in order
    BLOCK_CATEGORY_VOTE_MULTIPLIER = 5

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
        withdrawed_options = []
        for i in range(int(len(vote_str) / tab_size)):
            option = int(vote_str[i*tab_size: (i+1)*tab_size]) - 1

            if option in withdrawals:
                withdrawed_options.append(option)
                continue
            # blank vote
            elif option == len(question['answers']) + 1:
                raise BlankVoteException()
            # invalid vote
            elif option < 0 or option >= len(question['answers']):
                raise Exception()
            ret.append(option)

        # after removing withdrawed options, the vote might be empty but it 
        # would not have raised the BlankVoteException. Detect this case and
        # raise the exception in that case.
        if len(ret) == 0 and len(withdrawed_options) > 0:
            raise Exception()

        # detect invalid vote
        if len(ret) < question['min'] or len(set(ret)) != len(ret):
            raise Exception()
        if len(ret) > question['max']:
            if "truncate-max-overload" in question and question["truncate-max-overload"]:
                ret = ret[:question['max']]
            else:
                raise Exception()

        return ret

    def init_block_category_ballots(self, question):
        '''
        init the self.ballots with those that are category ballots
        '''
        # we will iterate the sorted list of answers to fill the dict of
        # categories with their ordered answer ids, then iterate the list of
        # categories to fill the self.ballots with the category ballots

        # ordered answers by id
        sorted_by_id = sorted(
            copy.deepcopy(question['answers']),
            key = lambda x: x['id']
        )

        # categories dict containing the list of their answer ids
        categories = dict()
        for answer in sorted_by_id:
            category = answer['category']
            if len(category) > 0:
                if category not in categories:
                    categories[category] = []
                categories[category].append(answer['id'])

        # finally, init the self.ballots with those that are category ballots
        for category in categories.values():
            self.ballots[str(category)] = dict(
                votes=0,
                answers=category,
                is_block_category_ballot=True
            )

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        question = questions[self.question_num]
        self.init_block_category_ballots(question)

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
            # if ballot found, increment the count. Else, create a ballot and
            # add it
            if key_answers in self.ballots:
                self.ballots[key_answers]['votes'] += 1
            else:
                self.ballots[key_answers] = dict(
                    votes=1,
                    answers=answers,
                    is_block_category_ballot=False
                )

    def masmadrid_tally(self, question, ballots):
        '''
        Executes the tally
        '''

        # initialize the electoral result fields in the answer list
        voters_by_position = [0] * question['max']
        for answer in question['answers']:
            answer['voters_by_position'] = copy.deepcopy(voters_by_position)
            answer['voters_as_block_category'] = 0
            answer['total_count'] = 0
            answer['winner_position'] = None

        # Number of base points for the first position in a vote
        #
        # NOTE: Using here 'max' instead of 'num_winners' as requested in
        # https://gitlab.nvotes.com/nvotes/pode-22/issues/15
        if 'bordas-max-points' not in question:
            base_max_points = question['max']
        else:
            base_max_points = question['bordas-max-points']

        # fill the 'voters_by_position' field on each answer
        for ballot_name, ballot in ballots.items():
            # "[50, 1, 4, 8]" :
            # {
            #   'votes': 4,
            #   'answers': [50, 1, 4, 8],
            #   'is_block_category_ballot': False
            # }
            question['totals']['valid_votes'] += ballot['votes']
            for index, option in enumerate(ballot['answers']):
                if ballot['votes'] == 0:
                    continue

                question['answers'][option]['voters_by_position'][index] += ballot['votes']

                multiplier = 1
                if ballot['is_block_category_ballot']:
                    question['answers'][option]['voters_as_block_category'] += ballot['votes']
                    multiplier = self.BLOCK_CATEGORY_VOTE_MULTIPLIER

                # do the total count, assigning base_points, base_points - 1,
                # etc for each vote, multiplying for 5 if it's a block category
                # ballot
                question['answers'][option]['total_count'] += (base_max_points - index) * multiplier * ballot['votes']

        # first order by the name of the eligible answers
        sorted_by_text = sorted(
            question['answers'],
            key = lambda x: x['text'])

        # then order in reverse by the total count
        sorted_winners = sorted(
            sorted_by_text,
            key = lambda x: x['total_count'],
            reverse = True)[:question['num_winners']]

        for winner_pos, winner in enumerate(sorted_winners):
            winner['winner_position'] = winner_pos

    def perform_tally(self, questions):
        self.report = {}
        report = self.report
        question = questions[self.question_num]
        self.masmadrid_tally(question, self.ballots)

    def post_tally(self, questions):
        '''
        '''
        self.perform_tally(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report
