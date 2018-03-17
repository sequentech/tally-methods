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
from .desborda2 import Desborda2Tally

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

class Desborda3Tally(Desborda2Tally):
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
    method_name = "Desborda3"
