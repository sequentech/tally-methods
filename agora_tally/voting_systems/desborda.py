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
import tempfile
from operator import itemgetter
from collections import defaultdict

from ..ballot_counter.ballots import Ballots
from ..ballot_counter.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException

# Definition of this system: 
# http://pabloechenique.info/wp-content/uploads/2016/12/DesBorda-sistema-Echenique.pdf
#
# Description:
# It's a modification of the Borda Count https://en.wikipedia.org/wiki/Borda_count
# It's a multiple winner election method in which voters rank candidates in order of preference.
# There will be 62 winners.
# Although each voter can create their ballot choosing the individual candidates,
# candidates are grouped into teams.
# Each team consists of 20 to 62 candidates, and they are presented in order, 
# although the voter can of course alter the order however he wants.
# Candidates can be either male or female. The first candidate of each team is
# a female and males and females are presented in a zipped way (f,m,f,m...)
# Each ballot can contain up to 62 candidates.
# On each ballot, the first candidate gets 80 points, and the last one 20.
# A second round can be done after correcting the minorities from the first  round.
# On the first round, teams that get more than 5% of all points and less than 2
# candidates elected will get their two most voted candidates  (female and male)
# elected.
# Also on the first round, teams that get more than 15% of the votes and less
# than 4 candidates elected, will get their 4 most voted candidates (2 females
# and 2 males).
# If there have been minorities corrections on the first round, there will be a
# second round. On the second round, the number of seats will be 62 minus the
# number of seats given to the minorities by the corrections.
# Likewise, on this second round all candidates from all teams that got seats on
# the first round because of the corrections will be withdrawn from all ballots
# on the second round. This means that if a ballot on the first round is:
# A1 (80 points), B6 (79 points), A2 (78 points)...
# and team B got elected B1 and B2 (but not B6, for example) on the first round
# because of a minorities correction, then on the second round this ballot
# would be:
# A1 (80 points), A2 (79 points)...
# because all candidates from team B are withdrawn for the second round, even
# those that didn't get elected.

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
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return DesbordaTally(election, question_num)

class DesbordaTally(BaseTally):
    '''
    Class used to tally an election
    '''
    ballots_file = None
    ballots_path = ""

    # list containing the current list of ballots.
    # In each iteration this list is modified. For efficiency, ballots with the
    # same ordered choices are grouped. The format of each item in this list is
    # the following:
    #
    #{
        #'votes': 12, # number of ballots with this selection of choices
        #'answers': [2, 1, 4] # list of ids of the choices
    #}
    ballots = []

    num_winners = -1

    # openstv options
    method_name = "Borda"

    # report object
    report = None

    def init(self):
        self.ballots_path = tempfile.mktemp(".blt")

        self.ballots = []

    def parse_vote(self, number, question, withdrawals=[]):
        vote_str = str(number)
        tab_size = len(str(len(question['answers']) + 2))

        # fix add zeros
        if len(vote_str) % tab_size != 0:
            num_zeros = (tab_size - (len(vote_str) % tab_size)) % tab_size
            vote_str = "0" * num_zeros + vote_str

        ret = []
        for i in range(int(len(vote_str) / tab_size)):
            option = int(vote_str[i*tab_size: (i+1)*tab_size]) - 1

            if option in withdrawals:
                continue
            # blank vote
            elif option == len(question['answers']) + 1:
                raise BlankVoteException()
            # invalid vote
            elif option < 0 or option >= len(question['answers']):
                raise Exception()
            ret.append(option)

        # detect invalid vote
        if len(ret) < question['min'] or len(set(ret)) != len(ret):
            raise Exception()
        if len(ret) > question['max']:
            if "truncate-max-overload" in question and question["truncate-max-overload"]:
                ret = ret[:question['max']]
            else:
                raise Exception()

        return ret

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        import codecs
        import os
        if not os.path.exists(os.path.dirname(self.ballots_path)):
            os.makedirs(os.path.dirname(self.ballots_path))

    def find_ballot(self, answers):
        '''
        Find a ballot with the same answers as the one given in self.ballots.
        Returns the ballot or None if not found.
        '''
        for ballot in self.ballots:
            if ballot['answers'] == answers:
                return ballot

        return None

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        answers = [choice+1 for choice in voter_answers[self.question_num]['choices']]
        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return

        ballot = self.find_ballot(answers)
        # if ballot found, increment the count. Else, create a ballot and add it
        if ballot:
            ballot['votes'] += 1
        else:
            self.ballots.append(dict(votes=1, answers=answers))

    def finish_writing_ballots_file(self, questions):
        # write the ballots
        self.ballots_file = codecs.open(self.ballots_path, encoding='utf-8', mode='w')
        question = questions[self.question_num]
        self.num_winners = question['num_winners']

        # write the header of the BLT File
        # See format here: https://code.google.com/p/droop/wiki/BltFileFormat
        self.ballots_file.write('%d %d\n' % (len(question['answers']), question['num_winners']))

        question = questions[self.question_num]
        for ballot in self.ballots:
            self.ballots_file.write('%d %s 0\n' % (ballot['votes'],
                ' '.join([str(a) for a in ballot['answers']])))
        self.ballots_file.write('0\n')

        # write the candidates
        for answer in question['answers']:
            name = answer['text']
            name.encode('utf-8')
            ans = u'"%s"\n' % name
            self.ballots_file.write(ans)

        q = '"%s"\n' % question['title'].replace("\n", "").replace("\"", "")
        q.encode('utf-8')
        self.ballots_file.write(q)
        self.ballots_file.close()

    def perform_tally(self, questions):
        '''
        Actually calls to openstv to perform the tally
        '''
        from ..ballot_counter.ballots import Ballots
        from ..ballot_counter.plugins import getMethodPlugins

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

        # run election and generate the report
        e.runElection()

        # generate report
        from .json_report import JsonReport
        self.report = JsonReport(e)
        self.report.generateReport()

    def fill_results(self, questions):

        json_report = self.report.json
        question = questions[self.question_num]
        question['totals']['valid_votes'] = json_report['ballots_count']
        def decode(s):
            if hasattr(s, 'decode'):
                return s.decode('utf-8')
            else:
                return s

        for answer in question['answers']:
            name = answer['text']
            name.encode('utf-8')

            answer['total_count'] = json_report['answers'][name]

        json_report['winners'] = [decode(winner) for winner in json_report['winners']]
        winner_answers = [answ for answ in question['answers'] if answ['text'] in json_report['winners']]
        # sort first by name then by total_count, that makes it reproducible
        winner_answers.sort(key=itemgetter('text'))
        winner_answers.sort(key=itemgetter('total_count'), reverse=True)
        json_report['winners'] = [answ['text'] for answ in winner_answers]

        votes_table = defaultdict(lambda:[0 for i in range(question['max'])])
        for ballot in self.ballots:
            votes = ballot['votes']
            for opti, opt in enumerate(ballot['answers']):
                votes_table[str(opt-1)][opti] += votes

        for answer in question['answers']:
          answer['voters_by_position'] = votes_table[str(answer['id'])]
          if answer['text'] in json_report['winners']:
            answer['winner_position'] = answer['text'].index(answer['text'])
          else:
            answer['winner_position'] = None

    def post_tally(self, questions):
        '''
        Once all votes have been added, this function actually save them to
        disk and then calls openstv to perform the tally
        '''
        self.finish_writing_ballots_file(questions)
        self.perform_tally(questions)
        self.fill_results(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report.json
