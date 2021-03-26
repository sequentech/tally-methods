#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# This file is part of agora-tally.
# Copyright (C) 2017-2021  Agora Voting SL <agora@agoravoting.com>

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
import tempfile

from agora_tally.ballot_codec.nvotes_codec import NVotesCodec
from agora_tally import file_helpers

def remove_spaces(in_str):
    return re.sub(r"[ \t\r\f\v]*", "", in_str)

def has_input_format(in_str):
     # example: "A1f, B2m \nB3f"
     m = re.fullmatch(r"(((\s*[A-Z][0-9]+[fm]\s*,)*\s*[A-Z][0-9]+[fm]\s*\n)|(\s*(b|i)\s*\n))*(((\s*[A-Z][0-9]+[fm]\s*,)*\s*[A-Z][0-9]+[fm]\s*\n?)|(\s*(b|i)\s*\n?))", in_str)
     return m is not None

def has_output_format(out_str):
     # example: "A1f, 1,  3\n B33m, 4"
     m = re.fullmatch(r"(\s*[A-Z][0-9]+[fm]\s*,\s*[0-9]+\s*\n)*\s*[A-Z][0-9]+[fm]\s*,\s*[0-9]+\s*\n?", out_str)
     return m is not None

def encode_valid_ballot(
    text_ballot, 
    indexed_results, 
    question
):
    for preference_position, candidate in enumerate(text_ballot):
        if candidate in indexed_results:
            indexed_results[candidate]["voters_by_position"][preference_position] += 1
   
    ballot_question = copy.deepcopy(question)
    for answer_index, answer in enumerate(ballot_question['answers']):
        answer['selected'] = (
            -1
            if answer['text'] not in text_ballot
            else text_ballot.index(answer['text'])
        )
    ballot_encoder = NVotesCodec(ballot_question)
    raw_ballot = ballot_encoder.encode_raw_ballot()
    int_ballot = ballot_encoder.encode_to_int(raw_ballot)
    return str(int_ballot + 1)

# generate password with length number of characters
def gen_pass(length):
  alphabet = string.ascii_letters + string.digits
  return ''.join(alphabet[c % len(alphabet)] for c in urandom(length))

def create_temp_folder():
    temp_folder = tempfile.mkdtemp()
    print("temp folder created at: %s" % temp_folder)
    return temp_folder

def create_desborda_test(test_data, tally_type = "desborda"):
    if not has_input_format(test_data["input"]):
        raise Exception("Error: test data input with format errors")
    if not has_output_format(test_data["output"]):
        raise Exception("Error: test data output with format errors")

    ballots = [
        re.split(r",", line) 
        for line in remove_spaces(test_data["input"]).splitlines()
    ]
    results = [
        re.split(r",", line) 
        for line in remove_spaces(test_data["output"]).splitlines()
    ]
    num_winners = 62
    if "num_winners" in test_data:
        num_winners = test_data["num_winners"]
    teams = {}
    all_candidates = []
    women = []
    num_blank_votes = 0
    num_invalid_votes = 0
    max_num = 0

    # first round of ballot processing. We count blank and invalid and collect 
    # candidate names and teams
    for ballot in ballots:
        len_ballot = len(ballot)
        if len_ballot > max_num:
            max_num = len_ballot
        if ['b'] == ballot:
           num_blank_votes += 1
           continue
        elif ['i'] == ballot:
           num_invalid_votes += 1
           continue
        for candidate in ballot:
            team = candidate[:1]
            female = ("f" == candidate[-1])
            if team not in teams:
                teams[team] = []
            else:
                other_sex = candidate[:-1] + ("m" if female else "f")
                if other_sex in teams[team]:
                    raise Exception(
                        "Error: candidate %s repeated: %s" % (
                            candidate, 
                            other_sex
                        )
                    )

            if candidate not in teams[team]:
                if female:
                    women.append(candidate)
                teams[team].append(candidate)
                all_candidates.append(candidate)

    if len(all_candidates) != len(set(all_candidates)):
        raise Exception("Error: all_candidates might have duplicate values")

    set_all = set(all_candidates)
    set_results = set([x[0] for x in results])
    if len(set_results) is not len(set_all & set_results):
        raise Exception(
            "Error: there are some answers in the results that are not "\
            "candidates: %s " % str(set_results - set_all)
        )

    question = {
        "answer_total_votes_percentage": "over-total-valid-votes",
        "answers": [],
        "description": "Desborda question",
        "layout": "simple",
        "max": max_num,
        "min": 0,
        "num_winners": num_winners,
        "randomize_answer_order": True,
        "tally_type": tally_type,
        "title": "Desborda question"
    }
    cand_index = 0
    indexed_candidates = {}
    for team_name in teams:
        team_candidates = teams[team_name]
        for candidate in team_candidates:
            answer = {
                "category": team_name,
                "details": candidate,
                "id": cand_index,
                "text": candidate,
                "urls": []
            }
            indexed_candidates[candidate] = cand_index
            question["answers"].append(answer)
            cand_index += 1

    questions_json = [question]

    num_ballots = len(ballots)
    results_json = {
      "questions": copy.deepcopy(questions_json),
      "total_votes": num_ballots
    }
    indexed_results = {}
    winner_position = 0
    voters_by_position = [0] * questions_json[0]["max"]
    for winner in results:
        indexed_results[winner[0]] = {
            "rounds": winner[1:],
            "winner_position": winner_position,
            "voters_by_position": copy.deepcopy(voters_by_position)
        }
        winner_position += 1

    # encode ballots in plaintexts_json format, and recreate voters_by_position
    plaintexts_json = ""
    
    # we use an encoder to create default ballots for a blank vote and null vote
    encoder = NVotesCodec(question)
    blank_vote_raw = encoder.encode_raw_ballot()
    blank_vote_int = encoder.encode_to_int(blank_vote_raw)

    null_vote_raw = copy.deepcopy(blank_vote_raw)
    null_vote_raw['choices'][0] = 1 # set the invalid vote flag
    null_vote_int = encoder.encode_to_int(null_vote_raw)

    for ballot in ballots:
        if ['i'] == ballot:
            encoded_ballot = str(null_vote_int + 1)
        elif ['b'] == ballot:
            encoded_ballot = str(blank_vote_int + 1)
        else:
            encoded_ballot = encode_valid_ballot(
                text_ballot=ballot, 
                indexed_results=indexed_results, 
                question=question
            )
        plaintexts_json = plaintexts_json + '"' + encoded_ballot + '"\n'

    for answer in results_json["questions"][0]["answers"]:
        candidate_name = answer["text"]
        if candidate_name not in indexed_results:
            answer["winner_position"] = None
            answer["total_count"] = 0
            answer["voters_by_position"] = copy.deepcopy(voters_by_position)
        else:
            answer["winner_position"] = indexed_results[candidate_name]["winner_position"]
            answer["total_count"] = int(indexed_results[candidate_name]["rounds"][-1])
            answer["voters_by_position"] = copy.deepcopy(indexed_results[candidate_name]["voters_by_position"])

    results_json["questions"][0]["totals"] = {
        "blank_votes": num_blank_votes,
        "null_votes": num_invalid_votes,
        "valid_votes": num_ballots - num_invalid_votes - num_blank_votes
    }
    results_json["questions"][0]["winners"] = []

    # create folder and files
    desborda_test_path = create_temp_folder()
    try:
        plaintexts_folder = os.path.join(desborda_test_path, "0-question")
        os.mkdir(plaintexts_folder)
        
        file_helpers.write_file(
            os.path.join(plaintexts_folder, "plaintexts_json"), 
            plaintexts_json
        )
        
        file_helpers.write_file(
            os.path.join(desborda_test_path, "questions_json"),
            file_helpers.serialize(questions_json)
        )

        file_helpers.write_file(
            os.path.join(desborda_test_path, "results_json"),
            file_helpers.serialize(results_json)
        )
    except:
        file_helpers.remove_tree(desborda_test_path)
        raise
    return desborda_test_path
