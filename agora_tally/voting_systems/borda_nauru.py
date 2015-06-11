from __future__ import unicode_literals
import random
import copy
import uuid
import sys
import codecs
import os
import tempfile
from operator import itemgetter
from collections import defaultdict

from openstv.ballots import Ballots
from openstv.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException
from .borda import BordaTally

class BordaNauru(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage an OpenSTV-based
    Nauru Borda voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'borda-nauru'

    @staticmethod
    def get_description():
        return _('Nauru Borda Count voting')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BordaNauruTally(election, question_num)

class BordaNauruTally(BordaTally):
    # openstv options
    method_name = "BordaNauru"