# self file is part of agora-tally.
#
# Copyright (C) 2021  Agora Voting SL <agora@agoravoting.com>
# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import copy
from operator import itemgetter

'''
Encodes/Decodes the answer to a question given the question type.
The encoder function always receives answer as a list of answer ids.
'''

VALID_CODECS = [
  "plurality-at-large", 
  "borda-nauru", 
  "borda", 
  "desborda3", 
  "desborda2", 
  "desborda", 
  "borda-mas-madrid",
  "cumulative"
]

class NVotesCodec(object):
  '''
  Used for encoding and decoding a question
  '''
  question = None

  def __init__(self, question):
    self.question = copy.deepcopy(question)

  def get_bases(self):
    '''
    Returns the bases related to this question.
    '''
    # sort answers by id
    sorted_answers = copy.deepcopy(self.question["answers"])
    sorted_answers.sort(key=itemgetter('id'))

    valid_answers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') not in answer.get('urls', [])
    ]

    # Calculate the base for answers. It depends on the 
    # `question.tally_type`:
    # - plurality-at-large: base 2 (value can be either 0 o 1)
    # - preferential (*bordas*): question.max + 1
    # - cummulative: question.max + 1
    answer_base = (
      2 
      if self.question["tally_type"] == "plurality-at-large" 
      else self.question["max"] + 1
    )

    # Set the initial bases and raw ballot, populate bases using the valid 
    # answers list
    bases = [2] + len(valid_answers)*[answer_base]

    # populate with byte-sized bases for the \0 end for each write-in
    if (
      "extra_options" in self.question and 
      "allow_writeins" in self.question["extra_options"] and
      self.question["extra_options"]["allow_writeins"] is True
    ):
      write_in_anwsers = [
        answer 
        for answer in sorted_answers
        if dict(title='isWriteIn', url='true') in answer.get('urls', [])
      ]
      bases.append(len(writeInAnwsers)*[256])

    return bases


class TestNVotesCodec(unittest.TestCase):
  def test_bases(self):
    # The question contains the minimum data required for the encoder to work
    data_list = [
      dict(
        question=dict(
          tally_type="plurality-at-large",
          answers=[
            dict(id=0),
            dict(id=1,selected=0),
            dict(id=2),
            dict(id=3),
            dict(id=4),
            dict(id=5, selected=1),
            dict(id=6)
          ]
        ),
        bases=[2, 2, 2, 2, 2, 2, 2, 2]
      ),
      dict(
        question=dict(
          tally_type="plurality-at-large",
          answers=[
            dict(id=0),
          ]
        ),
        bases=[2, 2]
      ),
      dict(
        question=dict(
          tally_type="borda",
          max=1,
          answers=[
            dict(id=0),
          ]
        ),
        bases=[2, 2]
      ),
      dict(
        question=dict(
          tally_type="borda",
          max=2,
          answers=[
            dict(id=0),
            dict(id=1),
            dict(id=2)
          ]
        ),
        bases=[2, 3, 3, 3]
      ),
    ]
    for data in data_list:
      codec = NVotesCodec(data["question"])
      self.assertEqual(codec.get_bases(), data["bases"])
