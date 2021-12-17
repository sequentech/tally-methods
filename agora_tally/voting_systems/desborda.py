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

from .base import BaseVotingSystem, BaseTally

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
        pass

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        answers = copy.deepcopy(voter_answers[self.question_num]['choices'])
        # do not count blank or invalid votes
        if (
            voter_answers[self.question_num]['is_blank'] or
            voter_answers[self.question_num]['is_null']
        ):
            return
        key_answers = str(answers)

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
            # "[50, 1, 4, 8]" : 
            # {
            #   'votes': 4
            #   'answers': [50, 1, 4, 8]
            # }
            question['totals']['valid_votes'] += ballot['votes']
            for index, option in enumerate(ballot['answers']):
                question['answers'][option]['voters_by_position'][index] += ballot['votes']

        # do the total count, assigning 80, 79, 78... points for each vote
        # on each answer depending on the position of the vote
        for answer in question['answers']:
            for index, num_voters in enumerate(answer['voters_by_position']):
                answer['total_count'] += (80-index) * num_voters

        # first order by the name of the eligible answers
        sorted_by_text = sorted(
            question['answers'],
            key = lambda x: x['text'])

        # then order in reverse by the total count
        sorted_winners = sorted(
            sorted_by_text,
            key = lambda x: x['total_count'],
            reverse = True)# [:question['num_winners']]

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
