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

import copy
from operator import itemgetter

from .base import (
    BaseVotingSystem, 
    BaseTally, 
    WeightedChoice, 
    get_key
)

# Definition of this system: 
# http://pabloechenique.info/wp-content/uploads/2016/12/DesBorda-sistema-Echenique.pdf

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
    def create_tally(question, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return DesbordaTally(question=question, question_num=question_num)

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


    def init(self):
        self.ballots = dict()

        def custom_subparser(decoded_ballot, question, withdrawals):
            answers = set()

            sorted_ballot_answers = copy.deepcopy(decoded_ballot['answers'])
            sorted_ballot_answers.sort(key=itemgetter('selected'))
            filtered_ballot_answers = [
                answer
                for answer in sorted_ballot_answers
                if answer['selected'] > -1 and answer['id'] not in withdrawals
            ]

            max_points = 80

            for index, answer in enumerate(filtered_ballot_answers):
                if answer['selected'] < 0 or answer['id'] in withdrawals:
                    continue

                answers.add(
                    WeightedChoice(
                        key=get_key(answer),
                        answer_id=answer['id'],
                        points=max(1, max_points - index)
                    )
                )
            return frozenset(answers)

        self.custom_subparser = custom_subparser

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        super().pre_tally(questions)
        
        # initialize voters_by_position
        question = questions[self.question_num]
        for answer in self.normal_answers.values():
            answer['voters_by_position'] = [0] * question['max']

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        super().add_vote(voter_answers, questions, is_delegated)

        if (
            voter_answers[self.question_num]['is_blank'] or
            voter_answers[self.question_num]['is_null']
        ):
            return

        # count voters by position
        question = questions[self.question_num]
        choices = voter_answers[self.question_num]['choices']
        choices = sorted(
            list(choices),
            key=lambda choice: choice.points,
            reverse=True
        )

        for choice_index, choice in enumerate(choices):
            answer = None

            if isinstance(choice.key, str):
                answer = self.write_in_answers[choice.key]
                # initialize voters_by_position if needed in write-ins
                if 'voters_by_position' not in answer:
                    answer['voters_by_position'] = [0] * question['max']
            else:
                answer = self.normal_answers[choice.key]
            answer['voters_by_position'][choice_index] += 1

    def post_tally(self, questions):
        super().post_tally(questions)
        question = questions[self.question_num]
        sorted_answers = sorted(
            question['answers'],
            key = lambda x: x['total_count'],
            reverse = True
        )
        for index, answer in enumerate(sorted_answers):
            answer['winner_position'] = index
