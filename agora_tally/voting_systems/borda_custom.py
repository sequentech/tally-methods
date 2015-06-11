from __future__ import unicode_literals
import random
import copy
import uuid
import sys
import codecs
import os
import tempfile
from operator import itemgetter

from openstv.ballots import Ballots
from openstv.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException
from .borda import BordaTally

class BordaCustom(BaseVotingSystem):
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
        return 'borda-custom'

    @staticmethod
    def get_description():
        return _('Custom Borda Count voting')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BordaCustomTally(election, question_num)

class BordaCustomTally(BordaTally):
    # openstv options
    method_name = "BordaCustom"
    weightByPosition = None
    
    def perform_tally(self, questions):
        '''
        Actually calls to openstv to perform the tally
        '''
        from openstv.ballots import Ballots
        from openstv.plugins import getMethodPlugins

        # get voting and report methods
        methods = getMethodPlugins("byName", exclude0=False)

        # generate ballots
        dirtyBallots = Ballots()
        dirtyBallots.loadKnown(self.ballots_path, exclude0=False)
        dirtyBallots.numSeats = self.num_winners
        cleanBallots = dirtyBallots.getCleanBallots()

        # create and configure election
        e = methods[self.method_name](cleanBallots)
        question = questions[self.question_num]
        e.maxChosableOptions = question['max']
        self.weightByPosition = question['borda_custom_weights']
        e.weightByPosition = self.weightByPosition

        # run election and generate the report
        e.runElection()

        # generate report
        from .json_report import JsonReport
        self.report = JsonReport(e)
        self.report.generateReport()
