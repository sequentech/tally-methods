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

from agora_tally.ballot_codec import mixed_radix
from test.file_helpers import serialize

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
      bases = bases + len(write_in_anwsers)*[256]

    return bases

  def encode_to_int(self, raw_ballot):
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
    return mixed_radix.encode(
      value_list=raw_ballot["choices"],
      base_list=raw_ballot["bases"]
    )

  def decode_from_int(self, int_ballot):
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
      if len(bases) < len(choices):
        choices.append(0)

      index = len(bases) + 1
      while index <= len(choices):
        bases.append(256)
        index += 1
    
    return dict(
      choices=choices,
      bases=bases
    )

  def encode_raw_ballot(self):
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
    invalid_vote_answer = (
      None
      if len(invalid_answers) == 0
      else invalid_answers[0]
    )
    invalid_vote_flag = (
      1 
      if (
        invalid_vote_answer is not None and 
        "selected" in invalid_vote_answer and 
        invalid_vote_answer["selected"] > -1
      )
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

    # populate raw_ballot and bases using the valid answers list
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
        choices.append(answer_value)
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
        choices.append(answer_value)
    
    # Populate the bases and the raw_ballot values with the write-ins 
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
          # we don't do a bases.append(256) as this is done in get_bases()
          # end it with a zero
          choices.append(0)
          continue

        encoded_text = answer["text"].encode('utf-8')
        for text_byte in encoded_text:
          bases.append(256)
          choices.append(text_byte)

        # End it with a zero. we don't do a bases.append(256) as this is done in 
        # get_bases()
        choices.append(0)

    return dict(
      bases=bases,
      choices=choices
    )
 
  def decode_raw_ballot(self, raw_ballot):
    '''
    Does the opposite of `encode_raw_ballot`.
    
    Returns `self.questions` with the data from the raw ballot.
    '''
    # 1. clone the question and reset the selections
    question = copy.deepcopy(self.question)
    for answer in question['answers']:
      answer['selected'] = -1

    # 2. sort & segment answers
    # 2.1. sort answers by id
    sorted_answers = question["answers"][:]
    sorted_answers.sort(key=itemgetter('id'))

    # 3. Obtain the invalidVote flag and set it
    valid_answers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') not in answer.get('urls', [])
    ]
    invalid_answers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') in answer.get('urls', [])
    ]
    invalid_vote_answer = (
      None 
      if len(invalid_answers) == 0
      else invalid_answers[0]
    )

    if invalid_vote_answer is not None:
      if raw_ballot["choices"][0] > 0:
        invalid_vote_answer["selected"] = 0
      else:
        invalid_vote_answer["selected"] = -1

    # 4. Do some verifications on the number of choices:
    #    Checking that the raw_ballot has as many choices as required
    min_num_choices = len(question["answers"])
    if len(raw_ballot["choices"]) < min_num_choices:
      raise Exception('Invalid Ballot: Not enough choices to decode')
    
    # 5. Obtain the vote for valid answers and populate the selections.
    valid_anwsers = [
      answer 
      for answer in sorted_answers
      if dict(title='invalidVoteFlag', url='true') not in answer.get('urls', [])
    ]

    # 5.1. Populate the valid answers. We asume they are in the same order as
    # in raw_ballot["choices"]
    for index, answer in enumerate(valid_answers):
      # we add 1 to the index because raw_ballot.choice[0] is just the
      # invalidVoteFlag
      choice_index = index + 1
      answer["selected"] = raw_ballot["choices"][choice_index] - 1

    # 6. Filter for the write ins, decode the write-in texts into 
    #    UTF-8 and split by the \0 character, finally the text for the
    #    write-ins.
    if (
      "extra_options" in question and 
      "allow_writeins" in question["extra_options"] and
      question["extra_options"]["allow_writeins"] is True
    ):
      write_in_answers = [
        answer 
        for answer in sorted_answers
        if dict(title='isWriteIn', url='true') in answer.get('urls', [])
      ]
      # if no write ins, return
      if len(write_in_answers) == 0:
        return question

      # 6.1. Slice the choices to get only the bytes related to the write ins
      write_in_raw_bytes = raw_ballot["choices"][len(question["answers"]):]

      # 6.2. Split the write-in bytes arrays in multiple sub-arrays 
      # using byte \0 as a separator.
      write_ins_raw_bytes_array = [ [] ]
      for index, byte_element in enumerate(write_in_raw_bytes):
        if byte_element == 0:
          # Start the next write-in byte array, but only if this is
          # not the last one
          if index != len(write_in_raw_bytes) - 1:
            write_ins_raw_bytes_array.append([])
        else:
          last_index = len(write_ins_raw_bytes_array) - 1
          write_ins_raw_bytes_array[last_index].append(byte_element)
      
      if len(write_ins_raw_bytes_array) != len(write_in_answers):
        raise Exception(
          "Invalid Ballot: invalid number of write-in bytes," +
          " len(write_ins_raw_bytes_array) = " + len(write_ins_raw_bytes_array) +
          ", len(write_in_answers) = " + len(write_in_answers)
        )

      # 6.3. Decode each write-in byte array
      write_in_decoded = [
        bytes(write_in_encoded_utf8).decode('utf-8')
        for write_in_encoded_utf8 in write_ins_raw_bytes_array
      ]

      # 6.4. Assign the write-in name for each write in
      for index, write_in_answer in enumerate(write_in_answers):
          write_in_answer["text"] = write_in_decoded[index]
    
    return question

  def sanity_check(self):
    '''
    Sanity check with a specific manual example, to see that encoding
    and decoding works as expected.
    
    Returns True if the test checks out or False otherwise.
    '''
    try:
      data = dict(
        question=dict(
          tally_type="plurality-at-large",
          max=3,
          extra_options=dict(allow_writeins=True),
          answers=[
            dict(id=0),
            dict(id=1),
            dict(id=2),
            dict(
              id=3,
              urls=[dict(title='invalidVoteFlag', url='true')]
            ),
            dict(
              id=4,
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=5,
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=6,
              urls=[dict(title='isWriteIn', url='true')]
            )
          ]
        ),
        ballot=dict(
          tally_type="plurality-at-large",
          max=3,
          extra_options=dict(allow_writeins=True),
          answers=[
            dict(id=0, selected=0 ),
            dict(id=1, selected=-1),
            dict(id=2, selected=-1),
            dict(
              id=3,
              selected=-1,
              urls=[dict(title='invalidVoteFlag', url='true')]
            ),
            dict(
              id=4,
              text='E',
              selected=0,
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=5,
              selected=-1,
              text='',
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=6,
              selected=0,
              text='Ä bc',
              urls=[dict(title='isWriteIn', url='true')]
            )
          ]
        ),
        raw_ballot=dict(
          bases=    [2, 2, 2, 2, 2, 2, 2, 256, 256, 256, 256, 256, 256, 256, 256, 256],
          choices=  [0, 1, 0, 0, 1, 0, 1, 69,  0,   0,   195, 132, 32,  98,  99,  0]
        ),
        int_ballot=916649230342635397842
      )

      # 1. encode from ballot to raw_ballot and test it
      encoder = NVotesCodec(data["ballot"])
      raw_ballot = encoder.encode_raw_ballot()
      if serialize(raw_ballot) != serialize(data["raw_ballot"]):
        raise Exception("Sanity Check fail")

      # 2. encode from raw_ballot to BigInt and test it
      int_ballot = encoder.encode_to_int(raw_ballot)
      if serialize(int_ballot) != serialize(data["int_ballot"]):
        raise Exception("Sanity Check fail")

      # 3. create a pristine encoder using the question without any selection 
      # set, and decode from BigInt to raw_ballot and test it
      decoder = NVotesCodec(data["question"])
      decoded_raw_ballot = decoder.decode_from_int(data["int_ballot"])
      if serialize(decoded_raw_ballot) != serialize(data["raw_ballot"]):
        raise Exception("Sanity Check fail")
      
      # 4. decode from raw ballot to ballot and test it
      decoded_ballot = decoder.decode_raw_ballot(decoded_raw_ballot)
      if serialize(decoded_ballot) != serialize(data["ballot"]):
        raise Exception("Sanity Check fail")

    except Exception as e:
      raise e
      # return False

    return True

  def biggest_encodable_normal_ballot(self):
    '''
    Returns the biggest encodable ballot that doesn't include any
    write-in text (or they are empty strings) encoded as a big int 
    voting to non-write-ins.
    
    Used to know if the ballot would overflow, for example during
    election creation, because it contains too many options.
    '''
    bases = self.get_bases()

    # calculate the biggest number that can be encoded with the 
    # minumum number of bases, which should be bigger than modulus
    highest_value_list = [base-1 for base in bases]
    highest_encoded_ballot = mixed_radix.encode(
      value_list=highest_value_list,
      base_list=bases
    )
    return highest_encoded_ballot

  def num_write_in_bytes_left(self, modulus):
    '''
    Returns the numbers of ASCII characters left to encode a number
    not bigger than the BigInt modulus given as input.
    '''
    # The calculations here do not make sense when there are no write-ins
    if (
      "extra_options" not in self.question or
      "allow_writeins" not in self.question["extra_options"] or
      self.question["extra_options"]["allow_writeins"] is False
    ):
      raise Exception("Contest does not have write-ins")

    # Sanity check: modulus needs to be bigger than the biggest 
    # encodable normal ballot
    bases = self.get_bases()
    highest_int = self.biggest_encodable_normal_ballot()
    if highest_int >= modulus:
      raise Exception("modulus too small")

    # If we decode the modulus bigint using the questions' mixed radix bases, 
    # the value will be garbage but the number of ints will be just 1 too many 
    # (as the last one will never be usable)
    decoded_modulus = mixed_radix.decode(
      base_list=bases,
      encoded_value=modulus,
      last_base=256
    )
    encoded_raw_ballot = self.encode_raw_ballot()
    max_len = len(decoded_modulus) - 1

    # As we know that the modulus is big enough for a ballot with no
    # write-ins and because we know all extra bases will be bytes,
    # the difference between the number of bases used for encoding the
    # ballot and the number of bases used to encode the modulus is the
    # number of byte bases left
    return max_len - len(encoded_raw_ballot.bases)


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

  def test_encode_raw_ballot(self):
    # The question contains the minimum data required for the encoder to work
    data_list = [
      dict(
        question=dict(
          tally_type="plurality-at-large",
          answers=[
            dict(id=0),
            dict(id=1, selected=0),
            dict(id=2),
            dict(id=3),
            dict(id=4),
            dict(id=5, selected=1),
            dict(id=6)
          ]
        ),
        bases=  [2, 2, 2, 2, 2, 2, 2, 2],
        choices=[0, 0, 1, 0, 0, 0, 1, 0]
      ),
      dict(
        question=dict(
          tally_type="plurality-at-large",
          answers=[
            dict(id=0,selected=0),
            dict(id=1,selected=0),
            dict(id=2),
            dict(id=3),
            dict(id=4),
            dict(id=5, selected=0),
            dict(id=6)
          ]
        ),
        bases=  [2, 2, 2, 2, 2, 2, 2, 2],
        choices=[0, 1, 1, 0, 0, 0, 1, 0]
      ),
      dict(
        question=dict(
          tally_type="borda",
          max=3,
          answers=[
            dict(id=0,selected=0),
            dict(id=1,selected=2),
            dict(id=2),
            dict(id=3),
            dict(id=4),
            dict(id=5, selected=1),
            dict(id=6)
          ]
        ),
        bases=  [2, 4, 4, 4, 4, 4, 4, 4],
        choices=[0, 1, 3, 0, 0, 0, 2, 0]
      ),
      dict(
        question=dict(
          tally_type="plurality-at-large",
          answers=[
            dict(id=0,selected=1),
            dict(id=1),
            dict(
              id=2,
              selected=1,
              urls=[dict(title='invalidVoteFlag', url='true')]
            )
          ]
        ),
        bases=  [2, 2, 2],
        choices=[1, 1, 0]
      ),
      dict(
        question=dict(
          tally_type="borda",
          max=2,
          extra_options=dict(allow_writeins=True),
          answers=[
            dict(id=0, selected=0),
            dict(id=1),
            dict(id=2),
            dict(
              id=3,
              selected=0,
              urls=[dict(title='invalidVoteFlag', url='true')]
            ),
            dict(
              id=4,
              text='D',
              selected=1,
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=5,
              text='',
              urls=[dict(title='isWriteIn', url='true')]
            )
          ]
        ),
        bases=     [2, 3, 3, 3, 3, 3, 256, 256, 256],
        choices=   [1, 1, 0, 0, 2, 0, 68,  0,   0]
      ),
      dict(
        question=dict(
          tally_type="plurality-at-large",
          extra_options=dict(allow_writeins=True),
          max=3,
          answers=[
            dict(id=0, selected=1),
            dict(id=1),
            dict(id=2),
            dict(
              id=3,
              urls=[dict(title='invalidVoteFlag', url='true')]
            ),
            dict(
              id=4,
              text='E',
              selected=1,
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=5,
              text='',
              urls=[dict(title='isWriteIn', url='true')]
            ),
            dict(
              id=6,
              selected=1,
              text='Ä bc',
              urls=[dict(title='isWriteIn', url='true')]
            )
          ]
        ),
        bases=    [2, 2, 2, 2, 2, 2, 2, 256, 256, 256, 256, 256, 256, 256, 256, 256],
        choices=  [0, 1, 0, 0, 1, 0, 1, 69,  0,   0,   195, 132, 32,  98,  99,  0]
      )
    ]
    for data in data_list:
      codec = NVotesCodec(data["question"])
      self.assertTrue(codec.sanity_check())

      # check raw ballot getter
      raw_ballot = codec.encode_raw_ballot()
      self.assertEqual(
        raw_ballot,
        dict(
          bases=data['bases'],
          choices=data['choices']
        )
      )
