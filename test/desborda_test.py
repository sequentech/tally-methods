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

import string
import re
import copy
import json
import os
from os import urandom
from test import file_helpers

def remove_spaces(in_str):
    return re.sub(r"[ \t\r\f\v]*", "", in_str)

def has_input_format(in_str):
     # example: "A1f, B2m \nB3f"
     m = re.fullmatch(r"((\s*[A-Z][0-9]+[fm]\s*,)*\s*[A-Z][0-9]+[fm]\s*\n)*(\s*[A-Z][0-9]+[fm]\s*,)*\s*[A-Z][0-9]+[fm]\s*", in_str)
     return m is not None

def has_output_format(out_str):
     # example: "A1f, 1,  3\n B33m, 4"
     m = re.fullmatch(r"(\s*[A-Z][0-9]+[fm]\s*,\s*[0-9]+\s*(,\s*[0-9]+\s*)?\n)*\s*[A-Z][0-9]+[fm]\s*,\s*[0-9]+\s*(,\s*[0-9]+\s*)?", out_str)
     return m is not None

def encode_ballot(ballot, indexed_candidates):
    max_num = len(indexed_candidates) + 2
    digit_num_per_candidate = len(str(max_num))
    encoded = ""
    for candidate in ballot:
        enc_cand = str(indexed_candidates[candidate] + 1)
        enc_cand = '0' * (digit_num_per_candidate - len(enc_cand)) + enc_cand
        encoded = encoded + enc_cand
    # note, only will work correctly on python 3
    return str(int(encoded) + 1)

# generate password with length number of characters
def gen_pass(length):
  alphabet = string.ascii_letters + string.digits
  return ''.join(alphabet[c % len(alphabet)] for c in urandom(length))

def create_rand_folder(base_path, add):
    if not (os.path.exists(base_path) and os.path.isdir(base_path)):
       raise Exception("base path %s doesn't exist, is not a folder or doesn't have the right permissions"  % base_path)
    folder_name = add + gen_pass(22)
    while os.path.exists(os.path.join(base_path, folder_name)):
        folder_name = add + gen_pass(22)
    final_path = os.path.join(base_path, folder_name)
    os.mkdir(final_path)
    return final_path

def create_desborda_test(test_data, fixtures_path):
    if not has_input_format(test_data["input"]):
        raise Exception("Error: test data input with format errors")
    if not has_output_format(test_data["output"]):
        raise Exception("Error: test data output with format errors")

    test_struct = {}
    test_struct["ballots"] = [re.split(r",", line) for line in remove_spaces(test_data["input"]).splitlines()]
    test_struct["results"] = [re.split(r",", line) for line in remove_spaces(test_data["output"]).splitlines()]
    test_struct["teams"] = {}
    test_struct["all_candidates"] = []
    test_struct["women"] = []
    for ballot in test_struct["ballots"]:
        for candidate in ballot:
            team = candidate[:1]
            female = "f" is candidate[-1]
            if team not in test_struct["teams"]:
                test_struct["teams"][team] = []
            else:
                other_sex = candidate[:-1] + ("m" if female else "f")
                if other_sex in test_struct["teams"][team]:
                    raise Exception("Error: candidate %s repeated: %s" % (candidate, other_sex))

            if female:
                test_struct["women"].append(candidate)

            test_struct["teams"][team].append(candidate)
            test_struct["all_candidates"].append(candidate)

    set_all = set(test_struct["all_candidates"])
    set_results = set([x[0] for x in test_struct["results"]])
    if len(set_results) is not len(set_all & set_results):
        raise Exception("Error: there are some answers in the results that are not candidates: %s " % str(set_results - set_all))

    question = {
        "answer_total_votes_percentage": "over-total-valid-votes",
        "answers": [],
        "description": "Desborda question",
        "layout": "simple",
        "max": 62,
        "min": 0,
        "num_winners": 62,
        "randomize_answer_order": True,
        "tally_type": "desborda",
        "title": "Desborda question"
    }
    cand_index = 0
    test_struct["indexed_candidates"] = {}
    for team_name in test_struct["teams"]:
        team_candidates = test_struct["teams"][team_name]
        for candidate in team_candidates:
            answer = {
                "category": team_name,
                "details": candidate,
                "id": cand_index,
                "text": candidate,
                "urls": []
            }
            test_struct["indexed_candidates"][candidate] = cand_index
            question["answers"].append(answer)
            cand_index += 1

    questions_json = [question]

    num_ballots = len(test_struct["ballots"])
    results_json = {
      "questions": copy.deepcopy(questions_json),
      "total_votes": num_ballots
    }
    test_struct["indexed_results"] = {}
    winner_position = 0
    voters_by_position = [0] * questions_json[0]["max"]
    for winner in test_struct["results"]:
        test_struct["indexed_results"][winner[0]] = {
            "rounds": winner[1:],
            "winner_position": winner_position,
            "voters_by_position": copy.deepcopy(voters_by_position)
        }
        winner_position += 1

    # encode ballots in plaintexts_json format, and recreate voters_by_position
    plaintexts_json = ""
    ballot_index = 1
    for ballot in test_struct["ballots"]:
        preference_position = 0
        for candidate in ballot:
            if candidate in test_struct["indexed_results"]:
               test_struct["indexed_results"][candidate]["voters_by_position"][preference_position] += 1
            preference_position += 1
        encoded_ballot = encode_ballot(ballot, test_struct["indexed_candidates"])
        plaintexts_json = plaintexts_json + '"' + encoded_ballot + '"'
        if num_ballots is not ballot_index:
            plaintexts_json = plaintexts_json + '\n'
        ballot_index += 1


    for answer in results_json["questions"][0]["answers"]:
        candidate_name = answer["text"]
        if candidate_name not in test_struct["indexed_results"]:
            answer["winner_position"] = None
            answer["total_count"] = 0
            answer["voters_by_position"] = copy.deepcopy(voters_by_position)
        else:
            answer["winner_position"] = test_struct["indexed_results"][candidate_name]["winner_position"]
            answer["total_count"] = test_struct["indexed_results"][candidate_name]["rounds"][-1]
            answer["voters_by_position"] = copy.deepcopy(test_struct["indexed_results"][candidate_name]["voters_by_position"])

    results_json["questions"][0]["totals"] = {
        "blank_votes": 0,
        "null_votes": 0,
        "valid_votes": num_ballots
    }
    results_json["questions"][0]["winners"] = []

    # create folder
    desborda_test_path = create_rand_folder(fixtures_path, "desborda_")
    try:
        plaintexts_folder = os.path.join(desborda_test_path, "0-question")
        os.mkdir(plaintexts_folder)
        file_helpers.write_file(os.path.join(plaintexts_folder, "plaintexts_json"), plaintexts_json)
        file_helpers.write_file(os.path.join(desborda_test_path, "questions_json"), file_helpers.serialize(questions_json))
        file_helpers.write_file(os.path.join(desborda_test_path, "results_json"), file_helpers.serialize(results_json))
    except:
        file_helpers.remove_tree(desborda_test_path)
        raise
    return desborda_test_path
