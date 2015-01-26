import random
import unittest
import codecs
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
    #MEEK_STV = "meek-stv"
    BORDA_NAURU = "borda-nauru"

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        do_tally.func_defaults[0][:] = []
        pass

    def _test_method(self, dirname):
        tally_path = os.path.join(self.FIXTURES_PATH, dirname)
        results_path = os.path.join(tally_path, "results_json")
        results = do_dirtally(tally_path)
        with codecs.open(results_path, encoding='utf-8', mode='r') as f:
            should_results = f.read()
        self.assertEqual(serialize(results), should_results)

    def test_borda_nauru(self):
        self._test_method(self.BORDA_NAURU)

    def test_plurality_at_large(self):
        self._test_method(self.PLURALITY_AT_LARGE)

if __name__ == '__main__':
    unittest.main()