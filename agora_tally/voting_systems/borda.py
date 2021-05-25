# This file is part of agora-tally.
# Copyright (C) 2013-2021  Agora Voting SL <agora@agoravoting.com>

# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

from .base import (
    BaseVotingSystem, 
    BaseTally, 
    WeightedChoice, 
    get_id_or_write_in
)

class Borda(BaseVotingSystem):
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
        return 'borda'

    @staticmethod
    def get_description():
        return _('Borda Count voting')

    @staticmethod
    def create_tally(question, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BordaTally(question=question, question_num=question_num)

class BordaTally(BaseTally):
    '''
    Class used to tally an election
    '''
    def init(self):
        def custom_subparser(decoded_ballot, question, withdrawals):
            answers = set()

            if 'bordas-max-points' not in question:
                max_points = question['max']
            else:
                max_points = question['bordas-max-points']

            for answer in decoded_ballot["answers"]:
                if answer['selected'] < 0 or answer['id'] in withdrawals:
                    continue

                answers.add(
                    WeightedChoice(
                        id_=get_id_or_write_in(answer),
                        points=(max_points - answer['selected'])
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
        for _, answer in self.normal_answers.items():
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

        if 'bordas-max-points' not in question:
            max_points = question['max']
        else:
            max_points = question['bordas-max-points']
        
        for choice_index, choice in enumerate(choices):
            answer = None
            
            if isinstance(choice.id, str):
                answer = self.write_in_answers[choice.id]
                # initialize voters_by_position if needed
                if 'voters_by_position' not in answer:
                    answer['voters_by_position'] = [0] * question['max']
            else:
                answer = self.normal_answers[choice.id]
            answer['voters_by_position'][choice_index] += 1
