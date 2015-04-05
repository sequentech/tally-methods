import random
import unittest
import codecs
import os
import copy
import json
from operator import itemgetter

from agora_tally.tally import do_tartally, do_dirtally, do_tally
from agora_tally.voting_systems.plurality_at_large import PluralityAtLarge
#from agora_tally.voting_systems.meek_stv import MeekSTV

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))

def _open(path, mode):
    return codecs.open(path, encoding='utf-8', mode=mode)

def _read_file(path):
    with _open(path, mode='r') as f:
        return f.read()

def _write_file(path, data):
    with _open(path, mode='w') as f:
        return f.write(data)

def _pretty_print_base(data, mark_winners, show_percent, filter_name):
    '''
    percent_base:
      "total" total of the votes, the default
      "valid options" votes to options
    '''
    def get_percentage(num, base):
      if base == 0:
          return 0
      else:
        return num*100.0/base

    counts = data['questions']
    for question, i in zip(counts, range(len(counts))):
        print("\n\nQ: %s\n" % question['title'])

        total_votes = data['total_votes']

        percent_base = question['answer_total_votes_percentage']
        if percent_base == "over-total-votes":
          base_num = data['total_votes']
        elif percent_base == "over-total-valid-votes":
          base_num = question['totals']['valid_votes']

        blank_votes = question['totals']['blank_votes']
        null_votes = question['totals']['null_votes']
        valid_votes = question['totals']['valid_votes']

        print("Total votes: %d" % total_votes)
        print("Blank votes: %d (%0.2f%%)" % (
            blank_votes,
            get_percentage(blank_votes, total_votes)))

        print("Null votes: %d (%0.2f%%)" % (
            null_votes,
            get_percentage(null_votes, total_votes)))

        print("Total valid votes (votes to options): %d (%0.2f%%)" % (
            valid_votes,
            get_percentage(valid_votes, total_votes)))
        print("\nOptions (percentages %s, %d winners):" % (percent_base, question['num_winners']))

        answers = sorted([a for a in question['answers']],
            key=lambda a: float(a['total_count']), reverse=True)

        for i, answer in zip(range(len(answers)), answers):
            print("%d. %s (%0.2f votes, %0.2f%%)" % (
                i + 1, answer['text'],
                answer['total_count'],
                get_percentage(answer['total_count'], base_num)))
    print("")

class TestSequenceFunctions(unittest.TestCase):
    FIXTURES_PATH = os.path.join("test", "fixtures")
    PLURALITY_AT_LARGE = "plurality-at-large"
    #MEEK_STV = "meek-stv"
    BORDA_NAURU = "borda-nauru"
    BORDA = "borda"
    BORDA2 = "borda2"
    BORDA_NAURU2 = "borda-nauru2"
    BORDA_CUSTOM = "borda-custom"
    maxDiff = None

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        do_tally.func_defaults[0][:] = []
        pass


    def _test_method(self, dirname):
        '''
        Generic method to do a tally
        '''
        tally_path = os.path.join(self.FIXTURES_PATH, dirname)
        results_path = os.path.join(tally_path, "results_json")
        results = do_dirtally(tally_path)
        should_results = _read_file(results_path)
        self.assertEqual(serialize(results), should_results)
        return results

    def test_borda_nauru(self):
        self._test_method(self.BORDA_NAURU)

    def test_borda_nauru2(self):
        '''
        Tests removing some candidates using a different input format
        '''
        WITHDRAWALS = ["25"]

        # first, generate questions_json
        base_path = os.path.join(self.FIXTURES_PATH, self.BORDA_NAURU2)
        candidates = _read_file(os.path.join(base_path, "raw_candidates.txt"))
        questions = json.loads(_read_file(os.path.join(base_path, "questions_base_json")))
        options = [line.split("\t")[0].strip() for line in candidates.split("\n")]

        for i, option in enumerate(options):
            questions[0]['answers'].append({
                "category": "",
                "details": "",
                "id": i,
                "text": option,
                "urls": []
            })
        questions[0]['max'] = len(options)
        questions[0]['num_winners'] = len(options) - 1
        _write_file(os.path.join(base_path, "questions_json"),
          serialize(questions))

        # serialize plaintexts
        raw_plaintexts_path = os.path.join(base_path, "0-question", "raw_plaintexts.txt")
        dst_plaintexts_path = os.path.join(base_path, "0-question", "plaintexts_json")
        fw = _open(dst_plaintexts_path, "w")

        with _open(raw_plaintexts_path, "r") as fr:
            for line in fr:
                num = "".join([str(int(opt.strip())-1).zfill(2)
                               for opt in line.split(",")
                               if opt.strip() not in WITHDRAWALS])
                if len(num) == 0:
                    num = len(questions[0]['answers']) + 2
                fw.write('"%d"\n' % (int(num) + 1))
        fw.close()
        results = self._test_method(self.BORDA_NAURU2)

        # print result
        _pretty_print_base(results, False, show_percent=True,
          filter_name="borda-nauru")
        os.unlink(dst_plaintexts_path)
        os.unlink(os.path.join(base_path, "questions_json"))

    def test_plurality_at_large(self):
          self._test_method(self.PLURALITY_AT_LARGE)

    def test_borda(self):
        self._test_method(self.BORDA)

    def test_borda2(self):
        self._test_method(self.BORDA2)
    
    def test_custom(self):
        self._test_method(self.BORDA_CUSTOM)

    #def test_meek_stv(self):
        #self._test_method(self.MEEK_STV)

if __name__ == '__main__':
    unittest.main()
