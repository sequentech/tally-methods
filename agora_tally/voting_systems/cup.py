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

from __future__ import unicode_literals, division
import random
import copy
import uuid
import sys
import codecs
import os
import tempfile
from operator import itemgetter

from .base import BaseVotingSystem, BaseTally, BlankVoteException



class Cup(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage an pairwise-beta election
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'cup'

    @staticmethod
    def get_description():
        return _('Cup')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return CupTally(election, question_num)

class CupTally(BaseTally):
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

    # report object
    report = None

    def init(self):
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
            if option == len(question['answers']) + 1:
                raise BlankVoteException()
            # invalid vote
            elif option < 0 or option >= len(question['answers']):
                raise Exception()
            ret.append(option)

        # detect invalid vote
        if len(ret) < question['min']:
            raise Exception()

        if len(ret) > question['max']:
            if "truncate-max-overload" in question and question["truncate-max-overload"]:
                ret = ret[:question['max'] * 2]
            else:
                raise Exception()

        return ret

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        pass


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
        answers = [choice for choice in voter_answers[self.question_num]['choices']]
        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return

        # don't count blank/invalid votes
        if len(answers) > 0:
            ballot = self.find_ballot(answers)
            # if ballot found, increment the count. Else, create a ballot and add it
            if ballot:
                ballot['votes'] += 1
            else:
                self.ballots.append(dict(votes=1, answers=answers))


    def perform_tally(self, questions):
        '''
        Runs the beta calculation
        '''

        self.report = {}
        report = self.report
        report['valid_votes'] = 0
        report['answers'] = {}
        question = questions[self.question_num]

        for a in question['answers']:
            a['total_count'] = 0
            a['total_votes'] = 0

        # get the presets in order
        preset_ids = [
          a['id'] for a in question['answers']
          if len(a['urls']) > 0 and a['urls'][0]['url'] == "https://agoravoting.com/api/tag/preset"]

        # count how many ballots have the preset
        preset_count = 0
        total_count = 0
        for ballot in self.ballots:
            if ballot['answers'][:len(preset_ids)] == preset_ids:
                preset_count += ballot['votes']
            total_count += ballot['votes']


        preset_approved = preset_count/total_count >= 0.55
        next_winner_pos = 0
        if preset_approved:
            next_winner_pos = len(preset_ids)
            for preset in preset_ids:
                question['answers'][preset]['winner_position'] = preset
                question['answers'][preset]['total_count'] = preset_count

            # withdraw candidates
            for ballot in self.ballots:
                ballot['answers'] = [a for a in ballot['answers'] if a not in preset_ids]

        question['totals']['valid_votes'] = total_count
        log = False
        for ballot in self.ballots:
            if log:
                print("ballot x%d:" % ballot['votes'])
            if ballot['answers'][:len(preset_ids)] == preset_ids:
                for i, a in enumerate(ballot['answers']):
                    answer = question['answers'][a]
                    prev_val = answer['total_count']
                    answer['total_votes'] += 1
                    if answer['id'] < len(preset_ids):
                        answer['total_count'] += 8*ballot['votes']
                        if log:
                            print("%d. %s = %d + %d*%d = %d" % (
                                i+1,
                                answer['text'].ljust(40),
                                prev_val,
                                8,
                                ballot['votes'],
                                answer['total_count']))
                    else:
                        answer['total_count'] += (len(ballot['answers']) - i)*ballot['votes']
                        if log:
                            print("%d. %s = %d + %d*%d = %d" % (
                                i+1,
                                answer['text'].ljust(40),
                                prev_val,
                                len(ballot['answers']) - i,
                                ballot['votes'],
                                answer['total_count']))
            else:
                for i, a in enumerate(ballot['answers']):
                    answer = question['answers'][a]
                    prev_val = answer['total_count']
                    answer['total_count'] += (len(ballot['answers']) - i)*ballot['votes']
                    answer['total_votes'] += 1
                    if log:
                        print("%d. %s = %d + %d*%d = %d" % (
                            i,
                            answer['text'].ljust(40),
                            prev_val,
                            len(ballot['answers']) - i,
                            ballot['votes'],
                            answer['total_count']))

        # set winner winner_position
        sorted_answers = sorted(question['answers'], key=itemgetter('total_count'), reverse=True)
        for a in sorted_answers:
            if a['id'] in preset_ids:
              a["preset_count"] = preset_count
            if preset_approved and a['id'] in preset_ids:
                continue

            if next_winner_pos >= question['num_winners']:
                a['winner_position'] = None
            else:
                a['winner_position'] = next_winner_pos
                next_winner_pos += 1

    def fill_results(self, questions):
        report = self.report
        question = questions[self.question_num]

        for answer in question['answers']:
            name = answer['text']
            id = answer['id']
            name.encode('utf-8')

    def post_tally(self, questions):
        '''
        Once all votes have been added, we carry out the tally
        '''
        self.perform_tally(questions)
        self.fill_results(questions)

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return self.report
