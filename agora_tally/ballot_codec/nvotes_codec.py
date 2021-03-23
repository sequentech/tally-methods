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

import agora_tally.ballot_codec.mixed_radix

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
      bases.append(len(write_in_nwsers)*[256])

    return bases

  def encode_to_int(raw_ballot):
    '''
    Converts a raw ballot into an encoded number ready to be encrypted. 
    A raw ballot is a list of positive integer numbers representing
    the ballot, and can be obtained calling to `self.encode_raw_ballot()`.
    
    Encoding is done using mixed radix encoding. The bases are 
    automatically calculated when instancing this object. The bases 
    used are either the number of points assigned to each answer or the
    position in which that answer was selected for preferential 
    elections. Please refer to mixed radix documentation to understand
    how it works or read https://en.wikipedia.org/wiki/Mixed_radix
    
    # Basics
    
    If in a `plurality-at-large` there are three candidates `A`, `B`,
    and `C` with answer ids `0`, `1` and `2`, and the voter wants to
    vote to candidates `A` and `C`, then his ballot choices (obtained
    using encode_raw_ballot) will be  `v = [1, 0, 1]` and the encoded 
    choices will be encoded this way:
    
    ```
    encoded_choices = v[0] + v[1]*b[0] + v[2]*b[0]*b[1]
    encoded_choices = v[0] + b[0]*(v[1] + b[1]*v[2])
    encoded_choices = 1 + 2*(0 + 2 * 1) = 1 + 4*1 = 5
    ```
    
    And the bases are `b = [2, 2, 2]`. The reason the bases are 2 here
    is because plurality-at-large is a non-preferential voting system
    and each base is representing if the voter chose (then we use 
    `v[x] = 1`) or not (then we use `v[x] = 0`), and the base is in 
    this case max(v[x])+1`.
    
    # Preferential systems
    
    In a preferential system, the voter can choose a specific ordering.
    If we reuse the previous example, the voter might have chosen for
    the first choice in his ballot candidate `A`, and for his second
    choice candidate `B`. Not choosing a candidate would be encoded as
    value `0`, so choosing it as first position would be value `1` and
    so on. If the voter can choose up to 3 candidates, then the base
    would be `maxChoices+1 = 3+1 = 4`, and thus bases will be 
    `b = [4, 4, 4]` and choices would be `v = [1, 0, 2]` and the
    encoded choices would be calculated as:
    
    ```
    encoded_choices = v[0] + v[1]*b[1] + v[2]*b[1]*b[2]
    encoded_choices = v[0] + b[0]*(v[1] + b[1]*v[2])
    encoded_choices = 1 + 4*(0 + 4*2) = 1 + 16*2 = 33
    ```
    
    # Invalid Ballot Flag
    
    What was outlined before is the basics, but actually it does not
    work exactly like that. The first value (`v[0]`) in the raw ballot
    does not really represent the vote for the first candidate answer,
    but it's always a flag saying if the ballot was marked as invalid
    or not by the voter. Note that this is not the only way to create
    an invalid ballot. For example the voter could vote to more options
    than allowed, and that would also be an invalid ballot.
    
    We asumes the invalid ballot flag is represented in the question
    as a answer inside `question.answers` and it is flagged  by having
    an element in `answer.urls` as 
    `{"title":'invalidVoteFlag', "url":'true'}`.
    
    Using the last example of a preferential vote, the bases would not
    be `b = [4, 4, 4]` but `b = [2, 4, 4, 4]` (the first base encodes
    always the invalid flag, whose max value is 1 so the base is always
    2).
    
    The choices would not be `v = [1, 0, 2]` but (if the vote was
    not marked as invalid) `v = [0, 1, 0, 2]` and thus the encoded
    choices would be calculated as:
    
    ```
    encoded_choices = v[0] + b[0]*(v[1] + b[1]*(v[2] + b[2]*v[3])
    encoded_choices = 0 + 2*(1 + 4*(0 + 4*2)) = 2*1 + 2*4*4*2
    encoded_choices = 2*1 + 32*2 = 66
    ```
    
    # Cumulative voting system
    
    In a cumulative voting system, the voter would have a total number
    of integer points to assign to candidates, and the voter can assign
    them to the available candidates with a maximum number of options
    that can be assigned to each candidate. 
    
    For example, the voter might be able to assign up to 2 points to
    each candidate and assign a total of 3 points. In practice, the
    encoding is done in a very similar format as with preferential 
    voting system. For each candidate, the value we assign is a number
    that represents the points assigned to the candidate, and the base
    used is the maximum number of assignable points plus one.
    
    Retaking the previous example used for plurality-at-large and used
    for a preferential voting system, if the voter can assign a 
    maximum of 4 points, and he wants to assign 2 points to candidate
    `A` and 2 points to candidate `C` and he didn't mark his ballot
    as invalid, then his choices would be `v = [0, 2, 0, 1]`, the bases 
    would be `b = [2, 5, 5, 5]` and the encoded choices would be 
    calculated as:
    
    ```
    encoded_choices = v[0] + b[0]*(v[1] + b[1]*(v[2] + b[2]*v[3])
    encoded_choices = 0 + 2*(2 + 5*(0 + 5*1)) = 2*2 + 2*5*5*1
    encoded_choices = 2*2 + 50*1 = 54
    ```
    
    # Write-ins
    
    This encoder supports write-ins. The idea of write-ins is that the
    voter can choose candidates that are not in the preconfigured list
    of candidates. The maximum number of write-ins allowed is 
    calculated automatically by suppossing the voter tries to 
    distribute his vote entirely just for write-in candidates, which
    is usually `question.max`.
    
    The vote for each write-in is encoded using the same procedure as
    for normal candidates, in order and as if the write-ins were in
    the list of candidates. It asumes all write-ins (even if not 
    selected) are in the list of candidates and they are flagged as 
    such simply by an element in `answer.urls` as
    `{"title":'isWriteIn', "url":'true'}`.
    
    For example in a plurality-at-large question example with three
    candidates `A`, `B` and `C` where the voter can choose up to 2
    candidates, if the voter wants to cast a valid ballot to his 2
    write-ins, then the bases, the choices and the encoded choices 
    would be:
    
    ```
    // bases
    b = [2, 2, 2, 2, 2, 2]
    // choices
    v = [0, 0, 0, 0, 1, 1]
    encoded_choices = 1*2^4 + 1*2^5 = 48
    ```
    
    # Write-in names
    
    Of course that's not where a vote with write-ins ends. If the voter
    voted to the write-ins, we would also have to encode the free text
    string of the name of the write-ins. This is done by converting the
    text from UTF-8 to numeric bytes, and encoding each byte using 
    2^8 = 256 as a base. The separation between the different write-in
    names is done using an empty byte (so `v[x] = 0`).
    
    So if in our case the name of the voter's two write-ins is `D` and
    `E`, and knowing that character D is encoded as number `68` and E
    is `69`, then the bases, the choices and the encoded choices
    would be:
    
    ```
    // bases
    b = [2, 2, 2, 2, 2, 2, 256, 256, 256, 256]
    // choices
    v = [0, 0, 0, 0, 1, 1, 68,  0,   69,  0]
    encoded_choices = 1*2^4 + 1*2^5 + 68*2^6 + 69*2^8 = 22064
    ```
    '''
    return mixedRadix.encode(
      value_list=raw_ballot["choices"],
      base_list=raw_ballot["bases"]
    )

  def decode_from_int(int_ballot):
    '''
    Does exactly the reverse of of encode_from_int. It should be
    such as the following statement is always true:
    
    ```
    data = codec.decode_from_int(
      codec.encode_from_int(raw_ballot)
    )
    ```
    
    This function is very useful for sanity checks.
    '''
    bases = self.get_bases()
    choices = mixed_radix.decode(
      base_list=bases,
      encoded_value=int_ballot,
      last_base=256
    )

    # minor changes are required for the write-ins
    if (
      "extra_options" in self.question and
      "allow_writeins" in self.question["extra_options"] and
      self.question["extra_options"]["allow_writeins"] is True
    ):
      # add missing byte bases and last \0 in the choices
      if bases.length < choices.length:
        choices.push(0)
      bases.append((choices.length - bases.length - 1) * [256]);
    
    return dict(
      choices=choices,
      bases=bases
    )

  def encode_raw_ballot():
    '''
    Returns the ballot choices and the bases to be used for encoding
    as an object, for example something like:
    
    ```
    dict(
      choices=[0, 0, 0, 0, 1, 1, 68,  0,   69,  0],
      bases=[  2, 2, 2, 2, 2, 2, 256, 256, 256, 256]
    )
    ```
    
    Please read the description of the encode function for details on
    the output format of the raw ballot.
    '''
    # sort answers by id
    sorted_answers = copy.deepcopy(self.question["answers"])
    sorted_answers.sort(key=itemgetter('id'))

    # Separate the answers between:
    # - Invalid vote answer (if any)
    # - Write-ins (if any)
    # - Valid answers (normal answers + write-ins if any)
    invalid_answers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') in answer.get('urls', [])
    ]
    invalid_vote_flag = (
      1 
      if invalid_vote_answer and invalid_vote_answer["selected"] > -1
      else 0
    )

    write_in_anwsers = [
      answer 
      for answer in sorted_answers
      if dict(title='isWriteIn', url='true') in answer.get('urls', [])
    ]

    valid_answers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') not in answer.get('urls', [])
    ]

    # Set the initial bases and raw ballot. We will populate the rest next
    bases = self.get_bases()
    choices = [invalid_vote_flag]

    # populate rawBallot and bases using the valid answers list
    tally_type = self.question["tally_type"]
    for answer in valid_answers:
      if tally_type == 'plurality-at-large':
        # We just flag if the candidate was selected or not with 1 for selected
        # and 0 otherwise
        answer_value = (
          0
          if (
            "selected" not in answer or
            answer["selected"] is None or
            answer["selected"] == -1
          )
          else 1
        )
        choices.push(answer_value)
      else:
        # we add 1 because the counting starts with 1, as zero means this 
        # answer was not voted / ranked
        answer_value = (
          0
          if (
            "selected" not in answer or
            answer["selected"] is None
          )
          else answer["selected"] + 1
        )
        choices.push(answer_value)
    
    # Populate the bases and the rawBallot values with the write-ins 
    # if there's any. We will through each write-in (if any), and then 
    # encode the write-in answer.text string with UTF-8 and use for 
    # each byte a specific value with base 256 and end each write-in 
    # with a \0 byte. Note that even write-ins.
    if (
      "extra_options" in self.question and
      "allow_writeins" in self.question["extra_options"] and
      self.question["extra_options"]["allow_writeins"] is True
    ):
      for answer in write_in_anwsers:
        if "text" not in answer or len(answer["text"]) == 0:
          # we don't do a bases.push(256) as this is done in get_bases()
          # end it with a zero
          choices.push(0)
          continue

        encoded_text = answer.text.encode('utf-8')
        for text_byte in encoded_text:
          bases.push(256)
          choices.push(text_byte)

        # End it with a zero. we don't do a bases.push(256) as this is done in 
        # get_bases()
        choices.push(0)

    return dict(
      bases=bases,
      choices=choices
    )


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
    

