import random

from .base import BaseVotingSystem, BaseTally, get_voting_system_by_id

class Plurality(BaseVotingSystem):
    '''
    Defines the helper functions that allows agora to manage a voting system.
    '''

    @staticmethod
    def get_id():
        '''
        Returns the identifier of the voting system, used internally to
        discriminate  the voting system used in an election
        '''
        return 'ONE_CHOICE'

    @staticmethod
    def get_description():
        return 'Choose one option among many - Technical name: Plurality voting system'

    @staticmethod
    def create_tally(election, question_num):
        '''
        Create object that helps to compute the tally
        '''
        return PluralityTally(election, question_num)


class PluralityTally(BaseTally):
    '''
    Class to tally an election
    '''
    dirty_votes = 0

    def pre_tally(self, result):
        '''
        Pre-proccess the tally
        '''
        question = result[self.question_num]
        for answer in question['answers']:
            answer['by_direct_vote_count'] = 0
            answer['by_delegation_count'] = 0

    def add_vote(self, voter_answers, result, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        question = result[self.question_num]
        for answer in question['answers']:
            if answer['value'] in voter_answers[self.question_num]["choices"]:
                answer['total_count'] += 1
                if is_delegated:
                    answer['by_delegation_count'] += 1
                else:
                    answer['by_direct_vote_count'] += 1
                break
        if not voter_answers[self.question_num]["choices"]:
            self.dirty_votes += 1

    def parse_vote(self, number, question):
        if number < 0:
            # invalid vote
            raise Exception()
        if number < len(question['answers']):
            option_str = question['answers'][number]['value']
        if number == len(question['answers']):
            raise BlankVoteException()
        elif number > len(question['answers']):
            # invalid vote
            raise Exception()

        return [option_str]

    def post_tally(self, result):
        '''
        Post process the tally
        '''
        # all votes counted, finish result will contain the actual result in
        # JSON format, something like:
        #[
            #{
                #"a": "question/result/ONE_CHOICE",
                #"answers": [
                    #{
                        #"a": "answer/result/ONE_CHOICE",
                        #"value": "Alice",
                        #"total_count": 33,
                        #"total_count_percentage": 73.4,
                        #"by_direct_vote_count": 25,
                        #"by_delegation_count": 8,
                        #"url": "<http://alice.com>", # UNUSED ATM
                        #"details": "Alice is a wonderful person who..." # UNUSED ATM
                    #},
                    #...
                #],
                #"max": 1, "min": 0,
                #"question": "Who Should be President?",
                #"randomize_answer_order": false, # true by default
                #"short_name": "President", # UNSED ATM
                #"tally_type": "ONE_CHOICE"
            #},
            #...
        #]

        # post process the tally adding additional information like total_count
        # in each answer, etc
        question = result[self.question_num]
        total_votes = 0
        winner = None

        for answer in question['answers']:
            total_votes += answer['total_count']
            if not winner or answer['total_count'] > winner['total_count']:
                winner = answer

        question['total_votes'] = total_votes
        question['dirty_votes'] = self.dirty_votes
        question['winners'] = [winner['value']]

        for answer in question['answers']:
            if total_votes > 0:
                answer['total_count_percentage'] = (answer['total_count'] * 100.0) / total_votes
            else:
                answer['total_count_percentage'] = 0