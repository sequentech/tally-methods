#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# This file is part of agora-tally.
# Copyright (C) 2017  Agora Voting SL <agora@agoravoting.com>

# agora-tally is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License.

# agora-tally  is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with agora-tally.  If not, see <http://www.gnu.org/licenses/>.

import codecs
import json
import shutil

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))

def open(path, mode):
    return codecs.open(path, encoding='utf-8', mode=mode)

def read_file(path):
    with open(path, mode='r') as f:
        return f.read()

def write_file(path, data):
    with open(path, mode='w') as f:
        return f.write(data)

def remove_tree(path):
    shutil.rmtree(path)