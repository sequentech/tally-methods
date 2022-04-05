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

import copy
from collections import defaultdict

from .base import (
    BaseVotingSystem, 
    BaseTally, 
    BlankVoteException,
    get_key,
    WeightedChoice
)

class Cumulative(BaseVotingSystem):
    '''
    Defines the helper functions that allows sequent to manage a
    cumulative voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'cumulative'

    @staticmethod
    def get_description():
        return _('Cumulative voting')

    @staticmethod
    def create_tally(question, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return CumulativeTally(
            question=question,
            question_num=question_num
        )

class CumulativeTally(BaseTally):
    '''
    Class used to tally a cumulative election
    '''
    def init(self):
        def custom_subparser(decoded_ballot, question, withdrawals):
            answers = set()

            for answer in decoded_ballot["answers"]:
                if answer['selected'] < 0 or answer['id'] in withdrawals:
                    continue

                answers.add(
                    WeightedChoice(
                        key=get_key(answer),
                        points=(answer['selected'] + 1),
                        answer_id=answer['id']
                    )
                )
            return frozenset(answers)

        self.custom_subparser = custom_subparser
