# This file is part of tally-methods.
#
# Copyright (C) 2021 Sequent Tech Inc <legal@sequentech.io>
#
# tally-methods is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# tally-methods  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with tally-methods.  If not, see <http://www.gnu.org/licenses/>.

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

def decode(base_list, encoded_value, last_base=None):
  '''
  Mixed number decoding. It will decode using multiple different bases.
  
  base_list     -- List of positive integer bases to use
  last_base     -- Base to use if base_list is too short
  encoded_value -- Integer value to decode
  
  Returns the list of positive decoded integer values
  '''
  decoded_values = []
  accumulator = encoded_value
  index = 0

  while accumulator > 0:
    base = base_list[index] if (index < len(base_list)) else last_base
    if index >= len(base_list) and last_base is None:
      raise Exception('Error decoding: last_base was needed but not provided')

    remainder = accumulator % base
    decoded_values.append(remainder)
    # use // to ensure it's treated as a big int division
    accumulator = (accumulator - remainder) // base
    index += 1

  # If we didn't run all the bases, fill the rest with zeros
  decoded_values.extend((len(base_list) - index)*[0])

  return decoded_values


class TestMixedRadix(unittest.TestCase):
  '''
  Unit tests related to the encode and decode functions
  '''
  data_list = [
    dict(
      value_list=[29, 23, 59],
      base_list= [30, 24, 60],
      encoded_value=(29 + 30*(23 + 24*59)), # 43199
      last_base=None
    ),
    dict(
      value_list=[10, 10, 10],
      base_list= [30,24, 60],
      encoded_value=7510, # = (10 + 30*(10 + 24*10))
      last_base=None
    ),
    dict(
      value_list=[21, 10, 11],
      base_list= [30, 24, 60],
      encoded_value=(21 + 30*(10 + 24*11)), # 8241
      last_base=None
    )
  ]

  def test_encode(self):
    for el in self.data_list:
      encoded_value = encode(
        value_list=el["value_list"],
        base_list=el["base_list"]
      )
      self.assertEqual(encoded_value, el["encoded_value"])
  
  def test_encode_error(self):
    '''
    Ensure encode function raises exception when value_list and base_list don't
    have the same length.
    '''
    self.assertRaises(
      Exception,
      encode, 
      value_list=[1,2], 
      base_list=[5, 5, 5]
    )
    self.assertRaises(
      Exception, 
      encode, 
      value_list=[1,2, 3, 3],
      base_list=[5, 5, 5]
    )
  
  def test_decode_error(self):
    '''
    Ensure that decode raises an exception if last_base is not given but is
    required.
    '''
    self.assertRaises(
      Exception, 
      encode,
      base_list=[2],
      encoded_value=3
    )
    self.assertRaises(
      Exception, 
      encode,
      base_list=[2,3],
      encoded_value=(2*3 + 1)
    )

  def test_decode(self):
    for el in self.data_list:
      decoded_value = decode(
        base_list=el["base_list"],
        encoded_value=el["encoded_value"],
        last_base=el['last_base']
      )
      self.assertEqual(decoded_value, el["value_list"])

  def test_encode_then_decode(self):
    data_list = [
      {
        "value_list": [21, 10, 11],
        "base_list":  [30, 24, 60],
        "encoded_value": 8241
      },
      {
        "value_list": [3, 2,  1 ],
        "base_list":  [5, 10, 10],
        "encoded_value": 63,
      },
      {
        "value_list": [1, 0, 2, 2, 128, 125, 0,   0  ],
        "base_list":  [3, 3, 3, 3, 256, 256, 256, 256],
        "encoded_value": 2602441
      },
      {
        "value_list": [0, 1, 2, 0],
        "base_list":  [3, 3, 3, 3],
        "encoded_value": 21,
      },
      {
        "value_list": [1, 0, 0,   0,   0,   0,   0  ],
        "base_list":  [2, 2, 256, 256, 256, 256, 256],
        "encoded_value": 1
      },
      {
        "value_list": [0, 1, 0, 0, 1, 0, 1, 69,],
        "base_list":  [2, 2, 2, 2, 2, 2, 2, 256],
        "encoded_value": (0 + 2*(1 + 2*(0 + 2*(0 + 2*(1 + 2*(0+ 2*(1 + 2*(69))))))))
      },
      {
        "value_list": [0, 1, 0, 0, 1, 0, 1, 69,  0,   0,   195, 132, 32,  98,  99,  0  ],
        "base_list":  [2, 2, 2, 2, 2, 2, 2, 256, 256, 256, 256, 256, 256, 256, 256, 256],
        # Value calculated in python3 that uses by default big ints for
        # integers. The formula is:
        # (0 + 2*(1 + 2*(0 + 2*(0 + 2*(1 + 2*(0+ 2*(1 + 2*(69 + 256*(0 + 256*(0 + 256*(195 + 256*(132 + 256*(32 + 256*(98+ 256*99))))))))))))))
        "encoded_value": 916649230342635397842
      }
    ]
    for example in data_list:
      encoded_value = encode(
        value_list=example["value_list"],
        base_list=example["base_list"]
      )
      decoded_value = decode(
        base_list = example["base_list"],
        encoded_value = encoded_value
      )

      self.assertEqual(encoded_value, example["encoded_value"])
      self.assertEqual(decoded_value, example["value_list"])
