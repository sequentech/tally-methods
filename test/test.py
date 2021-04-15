import random
import unittest
import codecs
import os
import copy
import json
import six
from operator import itemgetter

from agora_tally.tally import do_tartally, do_dirtally, do_tally
from agora_tally.voting_systems.plurality_at_large import PluralityAtLarge
from agora_tally import file_helpers
from agora_tally.ballot_codec.mixed_radix import TestMixedRadix
from agora_tally.ballot_codec.nvotes_codec import TestNVotesCodec

import test.desborda_test
import test.desborda_test_data

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
    CUMULATIVE = "cumulative"
    CUMULATIVE2 = "cumulative2"
    #MEEK_STV = "meek-stv"
    BORDA_NAURU = "borda-nauru"
    BORDA = "borda"
    BORDA2 = "borda2"
    BORDA_CUSTOM = "borda-custom"
    maxDiff = None

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        six.get_function_defaults(do_tally)[0][:] = []
        pass


    def _test_method(self, dirname):
        '''
        Generic method to do a tally
        '''
        tally_path = os.path.join(self.FIXTURES_PATH, dirname)
        results_path = os.path.join(tally_path, "results_json")
        results = do_dirtally(tally_path)
        should_results = file_helpers.read_file(results_path)
        self.assertEqual(file_helpers.serialize(results).strip(), should_results.strip())
        return results

    def test_borda_nauru(self):
        self._test_method(self.BORDA_NAURU)

    def test_plurality_at_large(self):
          self._test_method(self.PLURALITY_AT_LARGE)

    def test_cumulative(self):
          self._test_method(self.CUMULATIVE)

    def test_cumulative2(self):
          self._test_method(self.CUMULATIVE2)

    def test_borda(self):
        self._test_method(self.BORDA)

    def test_borda2(self):
        self._test_method(self.BORDA2)

    def test_custom(self):
        self._test_method(self.BORDA_CUSTOM)

class TestDesborda(unittest.TestCase):

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        six.get_function_defaults(do_tally)[0][:] = []
        pass

    def test_borda(self):
        # from the variables passed as arguments, create a folder with the data
        # in a format usable for tests
        tally_path = test.desborda_test.create_desborda_test(
            test.desborda_test_data.test_desborda_1
        )
        try:
            results = do_dirtally(tally_path)
            serialized_results = file_helpers.serialize(results)

            results_path = os.path.join(tally_path, "results_json")
            should_results = file_helpers.read_file(results_path)
            
            self.assertEqual(serialized_results, should_results)
            
            # remove the temp test folder also in a successful test
            file_helpers.remove_tree(tally_path)
        except:
            # if there was an error, recover from the exception at least to 
            # remove the previously created temp folder for the test
            file_helpers.remove_tree(tally_path)
            raise

    def test_desborda_blank_invalid(self):
        # from the variables passed as arguments, create a folder with the data
        # in a format usable for tests
        tally_path = test.desborda_test.create_desborda_test(
            test.desborda_test_data.test_desborda_2
        )
        try:
            results = do_dirtally(tally_path)
            serialized_results = file_helpers.serialize(results)

            results_path = os.path.join(tally_path, "results_json")
            should_results = file_helpers.read_file(results_path)
            
            self.assertEqual(serialized_results, should_results)
            
            # remove the temp test folder also in a successful test
            file_helpers.remove_tree(tally_path)
        except:
            # if there was an error, recover from the exception at least to 
            # remove the previously created temp folder for the test
            file_helpers.remove_tree(tally_path)
            raise

class TestDesborda2(unittest.TestCase):

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        six.get_function_defaults(do_tally)[0][:] = []
        pass

    def _do_test(self, data = None):
        if not data:
            return
        # from the variables passed as arguments, create a folder with the data
        # in a format usable for tests
        tally_path = test.desborda_test.create_desborda_test(
            data, # test.desborda_test_data.test_desborda2_1,
            tally_type = "desborda2")
        try:
            results_path = os.path.join(tally_path, "results_json")
            results = do_dirtally(tally_path)
            serialized_results = file_helpers.serialize(results)
            should_results = file_helpers.read_file(results_path)
            if serialized_results != should_results:
                print("results:\n" + serialized_results)
                print("shouldresults:\n" + should_results)
            self.assertEqual(serialized_results, should_results)
            # remove the temp test folder also in a successful test
            file_helpers.remove_tree(tally_path)
        except:
            # if there was an error, recover from the exception at least to 
            # remove the previously created temp folder for the test
            file_helpers.remove_tree(tally_path)
            raise

    def test1(self):
        self._do_test(test.desborda_test_data.test_desborda2_1)

    def test2(self):
        self._do_test(test.desborda_test_data.test_desborda2_2)

if __name__ == '__main__':
    unittest.main()
