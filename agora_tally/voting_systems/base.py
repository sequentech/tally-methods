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

from importlib import import_module

VOTING_METHODS = (
    #'agora_tally.voting_systems.meek_stv.MeekSTV',
    'agora_tally.voting_systems.plurality_at_large.PluralityAtLarge',
    'agora_tally.voting_systems.borda_nauru.BordaNauru',
    'agora_tally.voting_systems.borda.Borda',
    'agora_tally.voting_systems.cup.Cup',
    'agora_tally.voting_systems.borda_custom.BordaCustom',
    'agora_tally.voting_systems.pairwise_beta.PairwiseBeta',
    'agora_tally.voting_systems.pairwise_bradleyterry.PairwiseBradleyTerry',
    'agora_tally.voting_systems.desborda.Desborda',
    'agora_tally.voting_systems.desborda2.Desborda2',
    'agora_tally.voting_systems.desborda3.Desborda3'
)

def get_voting_system_classes():
    '''
    Returns a list with the available voting system classes
    '''
    ret_list = []
    for voting_method in VOTING_METHODS:
        mod_path, klass_name = voting_method.rsplit('.', 1)
        mod = import_module(mod_path)
        klass = getattr(mod, klass_name, None)
        ret_list.append(klass)
    return ret_list

def parse_voting_methods():
    '''
    Returns a tuple of pairs with the id and description of the voting system
    classes
    '''
    classes = get_voting_system_classes()
    return tuple(
        [(k.get_id(), k.get_description()) for k in classes]
    )

def get_voting_system_by_id(name):
    '''
    Returns the voting system klass given the id, or None if not found
    '''
    classes = get_voting_system_classes()
    for klass in classes:
        if klass.get_id() == name:
            return klass
    return None

class BaseVotingSystem(object):
    '''
    Defines the helper functions that allows agora to manage a voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'base'

    @staticmethod
    def get_description():
        '''
        Returns the user text description of the voting system
        '''
        pass

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return BaseTally(election, question_num)


class BaseTally(object):
    '''
    Class oser to tally an election
    '''
    election = None
    question_num = None
    question_id = None

    def __init__(self, election, question_num):
        self.election = election
        self.question_num = question_num
        self.init()

    def init(self):
        pass

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        pass

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        pass

    def parse_vote(self, number, question, withdrawals=[]):
        '''
        parse vote
        '''
        pass

    def post_tally(self, questions):
        '''
        Once all votes have been added, this function is called once
        '''
        pass

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return None

class BlankVoteException(Exception):
    pass
