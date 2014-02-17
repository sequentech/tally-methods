#!/usr/bin/env python

# Copyright (C) 2013 Eduardo Robles Elvira <edulix AT wadobo DOT com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from voting_systems.base import get_voting_system_by_id

import copy
import glob
import codecs
import tarfile
import json
import os
import sys
from tempfile import mkdtemp

def do_tartally(tally_path):
    dir_path = mkdtemp("tally")

    # untar the plaintexts
    tally_gz = tarfile.open(tally_path, mode="r:gz")
    paths = tally_gz.getnames()
    plaintexts_paths = [path for path in paths if path.endswith("/plaintexts_json")]

    member = tally_gz.getmember("result_json")
    member.name = "result_json"
    tally_gz.extract(member, path=dir_path)
    res_path = os.path.join(dir_path, 'result_json')
    with codecs.open(res_path, encoding='utf-8', mode='r') as res_f:
        result = json.loads(res_f.read())

    for plaintexts_path in plaintexts_paths:
        member = tally_gz.getmember(plaintexts_path)
        base = os.path.basename(os.path.dirname(plaintexts_path))
        subdir = os.path.join(dir_path, base)
        member.name = os.path.join(base, "plaintexts_json")
        os.makedirs(subdir)
        tally_gz.extract(member, path=dir_path)

    return do_tally(dir_path, result['counts'])

def do_dirtally(dir_path):
    res_path = os.path.join(dir_path, 'result_json')
    with codecs.open(res_path, encoding='utf-8', mode='r') as res_f:
        result = json.loads(res_f.read())

    return do_tally(dir_path, result['counts'])

def do_tally(dir_path, questions):
    # result is in the same format as get_result_pretty(). Initialized here
    result = copy.deepcopy(questions)
    base_vote =[dict(choices=[]) for q in result]

    # setup the initial data common to all voting system
    i = 0
    tallies = []
    for question in result:
        tally_type = question['tally_type']
        voting_system = get_voting_system_by_id(tally_type)
        tally = voting_system.create_tally(None, i)
        tallies.append(tally)

        question['a'] = "question/result/" + voting_system.get_id()
        question['winners'] = []
        question['total_votes'] = 0

        for answer in question['answers']:
            answer['a'] = "answer/result/" + voting_system.get_id()
            answer['total_count'] = 0
            answer['total_count_percentage'] = 0

        tally.pre_tally(result)
        plaintexts_path = os.path.join(dir_path, "%d*" % i, "plaintexts_json")
        plaintexts_path = glob.glob(plaintexts_path)[0]

        with codecs.open(plaintexts_path, encoding='utf-8', mode='r') as plaintexts_file:
            total_count = 0
            for line in plaintexts_file.readlines():
                total_count += 1
                voter_answers = base_vote
                try:
                    # Note line starts with " (1 character) and ends with
                    # "\n (2 characters). It contains the index of the
                    # option selected by the user but starting with 1
                    # because number 0 cannot be encrypted with elgammal
                    # so we trim beginning and end, parse the int and
                    # substract one
                    number = int(line[1:-2]) - 1
                    choices = tally.parse_vote(number, question)

                    # craft the voter_answers in the format admitted by
                    # tally.add_vote
                    voter_answers[i]['choices'] = choices
                except:
                    print "invalid vote: " + line
                    print "voter_answers = " + json.dumps(voter_answers)
                    import traceback; print traceback.format_exc()

                tally.add_vote(voter_answers=voter_answers,
                    result=result, is_delegated=False)

        i += 1


    extra_data = dict()

    # post process the tally
    for tally in tallies:
        tally.post_tally(result)

    return dict(
        a= "result",
        counts = result,
        total_votes = total_count,
        total_delegated_votes = 0
    )

if __name__ == "__main__":
    try:
        tally_path = sys.argv[1]
    except:
        print "usage: %s <tally_path>" % sys.argv[0]
        exit(1)

    if not os.path.exists(tally_path):
        print "tally path and/or questions_path don't exist"
        exit(1)
    print json.dumps(do_tartally(tally_path), indent=4)
