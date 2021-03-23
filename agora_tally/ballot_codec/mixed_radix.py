# This file is part of agora-tally.
#
# Copyright (C) 2021 Agora Voting SL <agora@agoravoting.com>
#
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

'''
This module implements mixed radix encoding and decoding with BigInt numbers
'''

def encode(value_list, base_list):
  '''
  Mixed number encoding. It will encode using multiple different bases. The
  number of bases and the number of values need to be equal.
  
  value_list -- List of positive integer number values to encode
  base_list  -- List of positive integer bases to use

  Returns the encoded number.
  '''
  # validate
  if len(value_list) != len(base_list):
    raise Exception(
      "Invalid parameters: 'value_list' and 'base_list' must have the same " + 
      "length."
    )

  # Encode
  encoded_value = 0
  index = len(value_list) - 1

  while index >= 0:
    encoded_value = (encoded_value * base_list[index]) + value_list[index]
    index -= 1
  return encoded_value

def decode(base_list, encoded_value, last_base):
  '''
  Mixed number decoding. It will decode using multiple different bases.
  
  base_list     -- List of positive integer bases to use
  last_base     -- Base to use if base_list is too short
  encoded_value -- Integer value to decode
  
  Returns the list of positive decoded integer values
  '''
  decodedValues = []
  accumulator = encoded_value
  index = 0

  while accumulator > 0:
    base = base_list[index] if (index < len(base_list)) else last_base

    decodedValues.append(accumulator % base)
    accumulator = accumulator / base
    index += 1

  # If we didn't run all the bases, fill the rest with zeros
  decodedValues.extend((len(base_list) - index)*[0])

  return decodedValues


class TestMixedRadix(unittest.TestCase):
  '''
  Unit tests related to the encode and decode functions
  '''

  def test_encode_1(self):
    encoded_val = encode(
      value_list=[29, 23, 59],
      base_list=[30,24, 60]
    )
    self.assertEqual(encoded_val, (29 + 30*(23 + 24*59)))
    self.assertEqual(encoded_val, 43199)
