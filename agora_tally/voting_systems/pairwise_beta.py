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



class PairwiseBeta(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage an pairwise-beta election
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'pairwise-beta'

    @staticmethod
    def get_description():
        return _('Pairwise Beta Binomial model')

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return PairwiseBetaTally(election, question_num)

class PairwiseBetaTally(BaseTally):
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

    def parse_vote(self, number, question):
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

        # detect invalid vote
        if len(ret) < question['min'] or len(ret) > question['max'] or\
                len(set(ret)) != len(ret) or len(ret) % 2 != 0:
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
        answers = [choice+1 for choice in voter_answers[self.question_num]['choices']]
        # we got ourselves an invalid vote, don't count it
        if -1 in answers:
            return

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

        # first collect wins and losses for each option
        for ballot in self.ballots:
            if len(ballot['answers']) % 2 == 0:
                report['valid_votes'] = report['valid_votes'] + ballot['votes']

                for idx, answer in enumerate(ballot['answers']):
                    if answer not in report['answers']:
                        report['answers'][answer] = dict(wins = 0, losses = 0, winner_position = None)
                    if idx % 2 == 0:
                        report['answers'][answer]['wins'] = report['answers'][answer]['wins'] + ballot['votes']
                    else:
                        report['answers'][answer]['losses'] = report['answers'][answer]['losses'] + ballot['votes']


        # calculate the beta posterior, see eq 38 in
        # http://www.cs.cmu.edu/~10701/lecture/technote2_betabinomial.pdf
        for answer in report['answers']:
            a = report['answers'][answer]
            a['score'] = (a['wins'] + 1) / (a['wins'] + 1 + a['losses'] + 1)

        ## obtain winners

        # first sort
        sorted_answers = sorted(report['answers'].items(), key = lambda a: a[1]['score'], reverse = True)

        question = questions[self.question_num]
        self.num_winners = question['num_winners']

        # mark winners
        for i in range(0, self.num_winners):
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
                answer['score'] = report['answers'][id]['score']
            else:
                answer['score'] = 0.0

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
