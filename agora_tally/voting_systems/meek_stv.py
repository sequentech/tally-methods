# This file is part of agora-tally.
# Copyright (C) 2013-2016  Agora Voting SL <agora@agoravoting.com>

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

from .base_stv import *

class MeekSTV(BaseSTV):
    '''
    Meek STV voting system
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'meek-stv'

    @staticmethod
    def get_description():
        return 'Multi-seat ranked voting - Meek STV (Single Transferable Vote)'

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        tally = BaseSTVTally(election, question_num)
        tally.method_name = "MeekSTV"
        return tally
