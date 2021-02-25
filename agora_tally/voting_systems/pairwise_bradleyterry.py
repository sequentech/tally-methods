from __future__ import unicode_literals, division
import random
import copy
import uuid
import sys
import codecs
import os
import tempfile
from operator import itemgetter
import subprocess

from .base import BaseVotingSystem, BaseTally, BlankVoteException

'''
R must be installed, as well as the BradleyTerry2 package

see http://www.jstatsoft.org/v48/i09/paper

> apt-get install r-base
> R
> install.packages('BradleyTerry2')
'''
class PairwiseBradleyTerry(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage a pairwise-bradleyterry election
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'pairwise-bradleyterry'

    @staticmethod
    def get_description():
        return _('Pairwise Bradley-Terry model')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return PairwiseBradleyTerryTally(election, question_num)

class PairwiseBradleyTerryTally(BaseTally):
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

    def parse_vote(self, number, question, q_withdrawals):
        vote_str = str(number)
        tab_size = len(str(len(question['answers']) + 2))

        # fix add zeros
        if len(vote_str) % tab_size != 0:
            num_zeros = (tab_size - (len(vote_str) % tab_size)) % tab_size
            vote_str = "0" * num_zeros + vote_str

        ret = []
        for i in range(int(len(vote_str) / tab_size)):
            option = int(vote_str[i*tab_size: (i+1)*tab_size]) - 1
            # blank vote
            if option == len(question['answers']) + 1:
                raise BlankVoteException()
            # invalid vote
            elif option < 0 or option >= len(question['answers']):
                raise Exception()
            ret.append(option)

        if len(ret) % 2 != 0:
            raise Exception()

        comparisons = len(ret) / 2

        # detect invalid vote
        if comparisons < question['min']:
            raise Exception()

        if comparisons > question['max']:
            if "truncate-max-overload" in question and question["truncate-max-overload"]:
                ret = ret[:question['max'] * 2]
            else:
                raise Exception()

        return ret

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''


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
        Fits the bradley-terry model
        '''

        self.report = {}
        report = self.report
        report['valid_votes'] = 0
        report['answers'] = {}
        report['pairs'] = {}

        # first collect wins and losses for each pair of options
        for ballot in self.ballots:
            if len(ballot['answers']) % 2 == 0:
                report['valid_votes'] = report['valid_votes'] + ballot['votes']

                for idx, answer in enumerate(ballot['answers']):
                    if idx % 2 == 0:
                        answer2 = ballot['answers'][idx + 1]

                        if answer < answer2:
                            key = "%s-%s" % (answer,answer2)
                            if key not in report['pairs']:
                                report['pairs'][key] = dict(wins1 = 0, wins2 = 0)

                            report['pairs'][key]['wins1'] = report['pairs'][key]['wins1'] + ballot['votes']

                        else:
                            key = "%s-%s" % (answer2,answer)
                            if key not in report['pairs']:
                                report['pairs'][key] = dict(wins1 = 0, wins2 = 0)

                            report['pairs'][key]['wins2'] = report['pairs'][key]['wins2'] + ballot['votes']

        # write pairs ready for bradleyterry
        pairs_path = tempfile.mktemp()
        with codecs.open(pairs_path, encoding='utf-8', mode='w') as pairs_file:
            for pair in report['pairs']:
                pairs_file.write('%s %s %s\n' % (pair.replace('-', ' '), report['pairs'][pair]['wins1'], report['pairs'][pair]['wins2']))

        # FIXME point to location of go.r
        output = subprocess.check_output(['Rscript', './agora_tally/voting_systems/go.r', pairs_path], stderr=None)

        os.remove(pairs_path)

        lines = output.split(b'\n')
        for line in lines:
            split = line.split()
            if len(split) == 3:
                option = int(split[0])
                score = float(split[1])
                report['answers'][option] = dict(score = score, winner_position = None)

        ## obtain winners

        # first sort
        sorted_answers = sorted(report['answers'].items(), key = lambda a: a[1]['score'], reverse = True)

        question = questions[self.question_num]
        self.num_winners = question['num_winners']

        # mark winners
        if len(sorted_answers) >= self.num_winners:
            to_mark = self.num_winners
        else:
            to_mark = len(sorted_answers)

        for i in range(0, to_mark):
            idx = sorted_answers[i][0]
            report['answers'][idx]['winner_position'] = i


    def fill_results(self, questions):

        report = self.report
        question = questions[self.question_num]
        question['totals']['valid_votes'] = report['valid_votes']

        for answer in question['answers']:
            name = answer['text']
            id = answer['id']
            name.encode('utf-8')

            if id in report['answers']:
                answer['total_count'] = report['answers'][id]['score']
            else:
                answer['total_count'] = 0.0

        for answer in question['answers']:
            id = answer['id']
            if id in report['answers']:
                answer['winner_position'] = report['answers'][id]['winner_position']
            else:
                answer['winner_position'] = None

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
