import random
import unittest
import os
import json

from agora_tally.tally import do_tartally, do_dirtally, do_tally
from agora_tally.voting_systems.plurality_at_large import PluralityAtLarge
#from agora_tally.voting_systems.meek_stv import MeekSTV

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))


class TestSequenceFunctions(unittest.TestCase):
    FIXTURES_PATH = os.path.join("test", "fixtures")
    PLURALITY_AT_LARGE = "plurality-at-large"
    MEEK_STV = "meek-stv"

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        do_tally.func_defaults[0][:] = []
        pass

    def test_plurality_at_large(self):
        tally_path = os.path.join(self.FIXTURES_PATH, self.PLURALITY_AT_LARGE)
        result = do_dirtally(tally_path)
        self.assertEqual(
            serialize(result),
            """{
    "questions": [
        {
            "answer_total_votes_percentage": "over-total-valid-votes",
            "answers": [
                {
                    "category": "",
                    "details": "",
                    "id": 1,
                    "text": "Alice",
                    "total_count": 3,
                    "urls": [],
                    "winner_position": null
                },
                {
                    "category": "",
                    "details": "",
                    "id": 2,
                    "text": "Bob",
                    "total_count": 4,
                    "urls": [],
                    "winner_position": 0
                },
                {
                    "category": "",
                    "details": "",
                    "id": 3,
                    "text": "Carmen",
                    "total_count": 1,
                    "urls": [],
                    "winner_position": null
                }
            ],
            "description": "Test question",
            "layout": "simple",
            "max": 2,
            "min": 0,
            "num_winners": 1,
            "randomize_answer_order": true,
            "tally_type": "plurality-at-large",
            "title": "Test question",
            "totals": {
                "blank_votes": 0,
                "null_votes": 1,
                "valid_votes": 6
            },
            "winners": []
        }
    ],
    "total_votes": 7
}"""
        )


    #def test_meek_stv(self):
        ## make sure the shuffled sequence does not lose any elements
        #tally_path = os.path.join(self.FIXTURES_PATH, self.MEEK_STV)
        #result = do_dirtally(tally_path)
        ## print(json.dumps(result, indent=4))

        #self.assertEqual(result['a'], 'result')
        #self.assertEqual(result['total_votes'], 7)

        #question = result['counts'][0]
        #self.assertEqual(question["winners"], ["Edward", "Bob"])
        #self.assertEqual(question["invalid_votes"], 3)
        #self.assertEqual(question["total_votes"], 4)

        # should raise an exception for an immutable sequence
        # self.assertRaises(TypeError, random.shuffle, (1,2,3))


if __name__ == '__main__':
    unittest.main()