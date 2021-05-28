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
from collections import defaultdict
import copy
from agora_tally.ballot_codec.nvotes_codec import NVotesCodec

VOTING_METHODS = (
    'agora_tally.voting_systems.plurality_at_large.PluralityAtLarge',
    'agora_tally.voting_systems.borda_nauru.BordaNauru',
    'agora_tally.voting_systems.borda.Borda',
    'agora_tally.voting_systems.borda_custom.BordaCustom',
    'agora_tally.voting_systems.desborda.Desborda',
    'agora_tally.voting_systems.desborda2.Desborda2',
    'agora_tally.voting_systems.desborda3.Desborda3',
    'agora_tally.voting_systems.cumulative.Cumulative',
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

class WeightedChoice:
    '''
    Represents a selection within a ballot, which is a pair of of an answer 
    and the number of checks selected.

    If the answer is a write-in, the answer will be a string, else it will be
    the answer id.
    '''
    def __init__(self, key, points, answer_id=None):
        self.key = key
        self.points = points
        self.answer_id = answer_id

    def __hash__(self):
        return hash((self.key, self.points))
    
    def __str__(self):
        return "WeightedChoice(key=%(key)r, points=%(points)r, answer_id=%(answer_id)r)" % dict(
            key=self.key,
            points=self.points,
            answer_id=self.answer_id
        )

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


def get_key(answer):
    '''
    If it's a write-in, returns the text of the write-in. Else,
    it returns the id.
    '''
    if dict(title='isWriteIn', url='true') in answer.get('urls', []):
        return answer['text']
    else:
        return answer['id']


class BaseTally(object):
    '''
    Class oser to tally an election
    '''
    question = None
    question_num = None
    question_id = None
    decoder = None
    custom_subparser = None

    def __init__(self, question, question_num):
        self.question = question
        self.question_num = question_num
        self.decoder = NVotesCodec(question)
        self.init()

    def init(self):
        pass

    def pre_tally(self, questions):
        '''
        Function called once before the tally begins
        '''
        question = questions[self.question_num]
        # initialize the counts
        for answer in question['answers']:
            answer['total_count'] = 0
            answer['winner_position'] = None

        # these are the answers that are not write-ins, so we can directly count
        # them
        self.normal_answers = dict([
            (answer['id'], copy.deepcopy(answer))
            for answer in question['answers']
            if dict(title='isWriteIn', url='true') not in answer.get('urls', [])
        ])

        # write_in_answers id's will start at this id + 1
        self.max_answer_id = max([answer['id'] for answer in question['answers']])
        
        # these are the write-in answers, and everytime a new write appears in
        # a ballot, we will have to add it here
        self.write_in_answers = dict()

    def parse_vote(
        self, 
        int_ballot, 
        question, 
        withdrawals=[]
    ):
        '''
        Parse vote
        '''
        raw_ballot = self.decoder.decode_from_int(int_ballot)
        decoded_ballot = self.decoder.decode_raw_ballot(raw_ballot)

        # detect if the ballot was marked as invalid, even if there's no 
        # explicit invalid answer
        if raw_ballot['choices'][0] > 0:
            raise Exception()
    
        non_blank_unwithdrawed_answers = None
        if self.custom_subparser is None:
            if not question.get("extra_options", dict()).get("allow_writeins", False):
                non_blank_unwithdrawed_answers = [
                    answer['id']
                    for answer in decoded_ballot['answers']
                    if answer['selected'] > -1 and answer['id'] not in withdrawals
                ]
            else:
                non_blank_unwithdrawed_answers = [
                    get_key(answer)
                    for answer in decoded_ballot['answers']
                    if answer['selected'] > -1 and answer['id'] not in withdrawals
                ]
        else:
            non_blank_unwithdrawed_answers = self.custom_subparser(
                decoded_ballot,
                question,
                withdrawals
            )

        if len(non_blank_unwithdrawed_answers) == 0:
            raise BlankVoteException()

        # detect and deal with different types of invalid votes
        if (
            len(non_blank_unwithdrawed_answers) < question['min'] or 
            len(set(non_blank_unwithdrawed_answers)) != len(non_blank_unwithdrawed_answers)
        ):
            raise Exception()

        truncate = False
        if len(non_blank_unwithdrawed_answers) > question['max']:
            if (
                "truncate-max-overload" in question and
                question["truncate-max-overload"]
            ):
                non_blank_unwithdrawed_answers = \
                    non_blank_unwithdrawed_answers[:question['max']]
                truncate = True
            else:
                raise Exception()
        
        # if panachage is disabled and vote is for answer of multiple categories
        # then it's an invalid vote
        enable_panachage = question\
            .get('extra_options', {})\
            .get('enable_panachage', True)
        if not enable_panachage:
            filtered_answer_categories = [
                answer["category"] 
                for answer in decoded_ballot['answers']
                if answer['selected'] > -1 and answer['id'] not in withdrawals
            ]
            if truncate:
                filtered_answer_categories = filtered_answer_categories[:question['max']]
            if len(set(filtered_answer_categories)) > 1:
                raise Exception()

        return non_blank_unwithdrawed_answers

    def add_vote(self, voter_answers, questions, is_delegated):
        '''
        Add to the count a vote from a voter
        '''
        question = questions[self.question_num]
        choices = voter_answers[self.question_num]['choices']
        if (
            not voter_answers[self.question_num]['is_blank'] and 
            not voter_answers[self.question_num]['is_null']
        ):
            question['totals']['valid_votes'] += 1
            for choice in choices:
                if isinstance(choice.key, str):
                    if choice.key in self.write_in_answers:
                        self.write_in_answers[choice.key]['total_count'] += choice.points
                    else:
                        self.write_in_answers[choice.key] = dict(
                            id=None, # this will be set later
                            text=choice.key,
                            category="",
                            details="",
                            total_count=choice.points,
                            winner_position=None,
                            urls=[
                                dict(title='isWriteInResult', url='true')
                            ]
                        )
                else:
                    # we can safely assume that the id is valid, as otherwise
                    # this would be counted as an invalid vote
                    self.normal_answers[choice.answer_id]['total_count'] += choice.points

    def post_tally(self, questions):
        '''
        Once all votes have been added, this function actually save them to
        disk and then calls openstv to perform the tally
        '''
        question = questions[self.question_num]

        # The counting is done, now we need to merge write-in answers and normal
        # answers in a reproducible way, and then assign winners. First, we need
        # to assign ids to the write ins.. and to do that sort them to make it
        # reproducible
        #
        # first sort by the name of the eligible answers
        write_ins_sorted_by_text = sorted(
            self.write_in_answers.values(),
            key = lambda x: x['text']
        )
        # then sort in reverse by the total count
        write_ins_sorted_by_text_and_total_count = sorted(
            write_ins_sorted_by_text,
            key = lambda x: x['total_count'],
            reverse = True
        )
        # finally assign write-in answers their new answer ids
        for index, answer in enumerate(write_ins_sorted_by_text_and_total_count):
            answer['id'] = self.max_answer_id + 1 + index

        # merge normal answers and write-ins
        final_answers = [
            self.normal_answers[answer_id]
            for answer_id in sorted(self.normal_answers.keys())
        ] + write_ins_sorted_by_text_and_total_count

        # change the question answers to these. NOTE that we will be removing
        # the write-in unfilled candidate options and adding the voted write-ins
        question['answers'] = final_answers

        final_answers_sorted_by_text = sorted(
            final_answers,
            key = lambda x: x['text']
        )
        # then sort in reverse by the total count and the first X are the 
        # winners!
        sorted_winners = sorted(
            final_answers_sorted_by_text,
            key = lambda x: x['total_count'],
            reverse = True
        )[:question['num_winners']]

        # .. so we assign winner positions
        for winner_pos, winner in enumerate(sorted_winners):
            winner['winner_position'] = winner_pos

    def get_log(self):
        '''
        Returns the tally log. Called after post_tally()
        '''
        return {}


class BlankVoteException(Exception):
    pass
