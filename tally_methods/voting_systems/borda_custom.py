# This file is part of tally-methods.
# Copyright (C) 2013-2021  Sequent Tech Inc <legal@sequentech.io>

# tally-methods is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# tally-methods  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with tally-methods.  If not, see <http://www.gnu.org/licenses/>.

from .base import (
    BaseVotingSystem, 
    BaseTally, 
    WeightedChoice, 
    ImplicitInvalidVoteException,
    get_key
)
from .borda import BordaTally

class BordaCustom(BaseVotingSystem):
    '''
    Defines the helper functions that allows sequent to manage an OpenSTV-based
    Nauru Borda voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'borda-custom'

    @staticmethod
    def get_description():
        return _('Custom Borda Count voting')

    @staticmethod
    def create_tally(question, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BordaCustomTally(
            question=question,
            question_num=question_num
        )

class BordaCustomTally(BordaTally):
    def init(self):
        def custom_subparser(decoded_ballot, question, withdrawals):
            answers = set()
            weights = question['borda_custom_weights']
            exception = None

            for answer in decoded_ballot["answers"]:
                if answer['selected'] < 0 or answer['id'] in withdrawals:
                    continue

                answers.add(
                    WeightedChoice(
                        key=get_key(answer),
                        points=weights[answer['selected']],
                        answer_id=answer['id']
                    )
                )
            
            # Check for invalid votes:
            selection = [
                answer['selected']
                for answer in decoded_ballot["answers"]
                if answer['selected'] >= 0
            ]
            # - no position is repeated
            if len(selection) != len(set(selection)):
                exception = 'implicit'

            selection_sorted = sorted(selection)
            should_be_selection_sorted = [
                index
                for index, _ in enumerate(selection_sorted)
            ]
            # - no missing position in-between
            if selection_sorted != should_be_selection_sorted:
                exception = 'implicit'

            ret_value = frozenset(answers)
            if exception is None:
                return ret_value
            else:
                raise ImplicitInvalidVoteException(ret_value)

        self.custom_subparser = custom_subparser
