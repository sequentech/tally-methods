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

import random
import copy
import uuid
import sys
import codecs
import os
import tempfile
from operator import itemgetter

from ..ballot_counter.ballots import Ballots
from ..ballot_counter.plugins import getMethodPlugins

from .base import BaseVotingSystem, BaseTally, BlankVoteException


class CumulativeBallot:
    def __init__(self, id_, checks):
        self.id = id_
        self.checks = checks

    def __hash__(self):
        return hash((self.id, self.checks))


class Cumulative(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage a
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
    method_name = "Approval"

    # report object
    report = None

    def init(self):
        self.ballots_path = tempfile.mktemp(".blt")
        self.ballots = []
        self.valid_votes = 0

        def custom_subparser(decoded_ballot, question, withdrawals):
            answers = []

            for answer in decoded_ballot["answers"]:
                if answer['selected'] < 0 or answer['id'] in withdrawals:
                    continue

                number = answer['selected'] + 1
                answers.append(CumulativeBallot(answer["id"], number))
            return answers

        self.custom_subparser = custom_subparser


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
        answers = voter_answers[self.question_num]['choices']
        if (
            not voter_answers[self.question_num]['is_blank'] and 
            not voter_answers[self.question_num]['is_null']
        ):
            self.valid_votes += 1

        for answer in answers:
            ballot = self.find_ballot([answer.id + 1])
            # if ballot found, increment the count. Else, create a ballot and add it
            if ballot:
                ballot['votes'] += answer.checks
            else:
                self.ballots.append(dict(votes=answer.checks, answers=[answer.id + 1]))

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
            answer['text'] = answer['text'].replace("\n", "").replace("\"", "")
            name = answer['text']
            name.encode('utf-8')
            ans = u'"%s"\n' % name
            self.ballots_file.write(ans)

        q = '"%s"\n' % question['title'].replace("\n", "").replace("\"", "")
        q.encode('utf-8')
        self.ballots_file.write(q)
        self.ballots_file.close()

    def perform_tally(self):
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

        # run election and generate the report
        e.runElection()

        # generate report
        from .json_report import JsonReport
        self.report = JsonReport(e)
        self.report.generateReport()

    def fill_results(self, questions):

        json_report = self.report.json
        question = questions[self.question_num]
        question['totals']['valid_votes'] = self.valid_votes
        def decode(s):
            if hasattr(s, 'decode'):
                return s.decode('utf-8')
            else:
                return s

        # we cant use ballots_count as there is more than one vote per ballot
        total_votes = 0
        for name in json_report['answers']:
            total_votes += json_report['answers'][name]

        for answer in question['answers']:
            name = answer['text'].replace("\n", "").replace("\"", "")
            name.encode('utf-8')

            answer['total_count'] = json_report['answers'][name]

        json_report['winners'] = [decode(winner) for winner in json_report['winners']]
        winner_answers = [answ for answ in question['answers'] if answ['text'] in json_report['winners']]
        # sort first by name then by total_count, that makes it reproducible
        winner_answers.sort(key=itemgetter('text'))
        winner_answers.sort(key=itemgetter('total_count'), reverse=True)
        json_report['winners'] = [answ['text'] for answ in winner_answers]

        for answer in question['answers']:
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
        self.perform_tally()
        self.fill_results(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report.json