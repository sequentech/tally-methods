import random
import unittest
import os
import json

from agora_tally.tally import do_tartally, do_dirtally, do_tally
from agora_tally.voting_systems.plurality import Plurality
from agora_tally.voting_systems.meek_stv import MeekSTV


class TestSequenceFunctions(unittest.TestCase):
    FIXTURES_PATH = os.path.join("test", "fixtures")
    PLURALITY = "plurality"
    MEEK_STV = "meek-stv"
    APPROVAL = "approval"

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        do_tally.func_defaults[0][:] = []
        pass

    def test_plurality(self):
        # make sure the shuffled sequence does not lose any elements
        tally_path = os.path.join(self.FIXTURES_PATH, self.PLURALITY)
        result = do_dirtally(tally_path)
        # print(json.dumps(result, indent=4))

        self.assertEqual(result['a'], 'result')
        self.assertEqual(result['total_votes'], 6)
        self.assertEqual(len(result['counts']), 1)

        question = result['counts'][0]
        self.assertEqual(question['tally_type'], Plurality.get_id())
        self.assertEqual(len(question['answers']), 2)
        alice = question['answers'][0]

        self.assertEqual(alice["total_count"], 1)
        self.assertEqual(alice["value"], "Alice")
        self.assertAlmostEqual(alice["total_count_percentage"], 100/3.0, 3)

        bob = question['answers'][1]

        self.assertEqual(bob["total_count"], 2)
        self.assertEqual(bob["value"], "Bob")
        self.assertAlmostEqual(bob["total_count_percentage"], 200/3.0, 3)

        self.assertEqual(len(question["winners"]), 1)
        self.assertEqual(question["winners"][0], "Bob")
        self.assertEqual(question["dirty_votes"], 3)
        self.assertEqual(question["invalid_votes"], 3)
        self.assertEqual(question["total_votes"], 3)

        # should raise an exception for an immutable sequence
        # self.assertRaises(TypeError, random.shuffle, (1,2,3))

    def test_meek_stv(self):
        # make sure the shuffled sequence does not lose any elements
        tally_path = os.path.join(self.FIXTURES_PATH, self.MEEK_STV)
        result = do_dirtally(tally_path)
        # print(json.dumps(result, indent=4))

        self.assertEqual(result['a'], 'result')
        self.assertEqual(result['total_votes'], 7)

        question = result['counts'][0]
        self.assertEqual(question["winners"], ["Edward", "Bob"])
        self.assertEqual(question["invalid_votes"], 3)
        self.assertEqual(question["total_votes"], 4)

        # should raise an exception for an immutable sequence
        # self.assertRaises(TypeError, random.shuffle, (1,2,3))


    def test_approval(self):
        # make sure the shuffled sequence does not lose any elements
        tally_path = os.path.join(self.FIXTURES_PATH, self.APPROVAL)
        result = do_dirtally(tally_path)
        # print(json.dumps(result, indent=4))

        self.assertEqual(result['a'], 'result')
        self.assertEqual(result['total_votes'], 7)

        question = result['counts'][0]
        # because plurality at large is not a preferential vote, the results are reversed wrt. to stv
        self.assertEqual(question["winners"], ["Bob", "Edward"])
        self.assertEqual(question["invalid_votes"], 3)
        self.assertEqual(question["total_votes"], 4)


    '''def test_choice(self):
        element = random.choice(self.seq)
        self.assertTrue(element in self.seq)

    def test_sample(self):
        with self.assertRaises(ValueError):
            random.sample(self.seq, 20)
        for element in random.sample(self.seq, 5):
            self.assertTrue(element in self.seq)
    '''
if __name__ == '__main__':
    import xmlrunner
    unittest.main(testRunner=xmlrunner.XMLTestRunner(output='report'))
