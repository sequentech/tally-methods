import random
import unittest
import codecs
import os
import copy
import json
from operator import itemgetter

from agora_tally.tally import do_tartally, do_dirtally, do_tally
from agora_tally.voting_systems.plurality_at_large import PluralityAtLarge
from agora_tally.voting_systems.meek_stv import MeekSTV

def serialize(data):
    return json.dumps(data,
        indent=4, ensure_ascii=False, sort_keys=True, separators=(',', ': '))

def _open(path, mode):
    return codecs.open(path, encoding='utf-8', mode=mode)

def _read_file(path):
    with _open(path, mode='r') as f:
        return f.read().replace('\r\n', "\n")

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
    FIXTURES_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "fixtures")
    PLURALITY_AT_LARGE = "plurality-at-large"
    MEEK_STV = "meek-stv"
    BORDA_NAURU = "borda-nauru"
    BORDA = "borda"
    BORDA2 = "borda2"
    BORDA_NAURU2 = "borda-nauru2"
    BORDA_CUSTOM = "borda-custom"
    PAIRWISE_BETA = "pairwise-beta"
    PAIRWISE_BRADLEYTERRY = "pairwise-bradleyterry"
    maxDiff = None

    def setUp(self):
        # http://effbot.org/zone/default-values.htm
        do_tally.func_defaults[0][:] = []
        pass


    def _test_method(self, dirname):
        """Agora-Voting:  Generic method to do a tally
        SOD: this method compares the results of applies do_dirtally method to a specific questions_json (in the
        path determined from tally_path) with the results save in the results_json file and, if they are the same
        result, returns one of them (in the method, it returns the variable called results but it could be
        should_results too)"""

        tally_path = os.path.join(self.FIXTURES_PATH, dirname)
        results = do_dirtally(tally_path)
        results_path = os.path.join(tally_path, "results_json")
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

    # broken
    #def test_borda2(self):
    #    self._test_method(self.BORDA2)

    def test_pairwise_beta(self):
        self._test_method(self.PAIRWISE_BETA)

    #def test_pairwise_bradleyterry(self):
    #    self._test_method(self.PAIRWISE_BRADLEYTERRY)

    #def test_custom(self):
    #    self._test_method(self.BORDA_CUSTOM)

    def test_meek_stv(self):
        results = self._test_method(self.MEEK_STV)
        print("MEEK-STV TEST")
        for question in results['questions']:
            varQuestion = question['question']
            varWinners = question['winners']
            print("Question: " + varQuestion)
            print("Winners:")
            i = 1
            for winner in varWinners:
                stringI = str(i)
                print(stringI + ". " + winner)
                i = i+1
        print("-----------")


    #SOD: We use this test to check the correct performance of the meek-stv recount when we have more than one question.
    #In this case, the system reads the votes of the plaintexts_json according to the question's index. If the question is
    #in the first position (index=0), the system reads the votes of the directory "0-question"
    def test_meek_stvMultipleQuestions(self):
        tally_path = os.path.join(self.FIXTURES_PATH+'/meek-stv-multipleQuestions')
        results = do_dirtally(tally_path)
        index = 0
        print("MEEK-STV TEST MULTIPLE QUESTIONS")
        for question in results['questions']:
            varQuestion = question['question']
            varWinners = question['winners']
            varBlankVotes = question['totals']['blank_votes']
            print("Question: " + varQuestion)
            print("Blank Votes: " + str(varBlankVotes))
            print("Winners:")
            i = 1
            for winner in varWinners:
                stringI = str(i)
                print(stringI + ". " + winner)
                i = i+1
        print("----------------")



    """Agora-Voting:  method to testing the invalid votes
        JAAL: this method compares the results of applies do_dirtally method,
        to a specific purposely value since the 'plaintexts_json' file.
        if the comparison result is correct, the test is verified."""
    def test_invalid_votesMeekstv(self):

        tally_path = os.path.join(self.FIXTURES_PATH+'/meek-stv-invalidVotes')
        results = do_dirtally(tally_path)
        self.assertTrue('"null_votes": 2,' in serialize(results))

    """Agora-Voting:  method to testing the blank votes
        JAAL: this method compares the results of applies do_dirtally method,
        to a specific purposely value since the 'plaintexts_json' file.
        if the comparison result is correct, the test is verified."""
    def test_blank_votesMeekstv(self):
        tally_path = os.path.join(self.FIXTURES_PATH+'/meek-stv-blankVotes')
        results = do_dirtally(tally_path)
        self.assertTrue('"blank_votes": 1,' in serialize(results))

    def test_many_votes(self):
        tally_path = os.path.join(self.FIXTURES_PATH+'/meek-stv-manyVotes')

        # We generate 5238 random votes, where we want 3 candidates to have different weight than the others
        generateVotes({4:50, 3:20, 15:12}, 5238, 25, tally_path)
        results = do_dirtally(tally_path)
        winners = serialize(results).split('"winners": ')[1]
        #Now we just check if the three candidates with more votes are the winners
        self.assertTrue("Eduardo Bondad" in winners)
        self.assertTrue("Juan Jesus Lopez Aguilar" in winners)
        self.assertTrue("Javier" in winners)
        '''You can check the different votes in the plaintexts_json in meek-stv-manyVotes to check that the result is
        randomly generated. It even includes blank votes and invalid votes. The results are generated in a file as well
        if you want to check some statistics or just to see if they're being generated correctly.'''
        _write_file(tally_path+"/results_json", serialize(results))

if __name__ == '__main__':
    unittest.main()

# Method for generating a result file with random votes:

import random

def weighted_choice(choices):
    #A simple algorithm that takes a dictionary with Choice : Weight and gives a weighted random choice.
    r = random.uniform(0, sum(choices.itervalues()))
    s = 0
    for k, w in choices.iteritems():
        s+=w
        if r < s: return k
    return k



def generateVotes(weights, numberOfVotes, numberOfAnswers, filedir):
    target = ""
    #We create a great enough weight for having hundreds of blank votes
    weights[numberOfAnswers+1]=5
    #Then we assign an equal weight to all the options without weights
    while numberOfAnswers>0:
        if not numberOfAnswers in weights:
            weights[numberOfAnswers]= 1
        numberOfAnswers-=1
    weights[0]=1
    #Finally for every vote we calculate a random weighted choice
    for x in xrange(numberOfVotes):
        vote = weighted_choice(weights)+1
        if vote == 1:
            vote = "garbage"
        target += '"'+str(vote)+'"\n'
    #And write it in a file for reading
    _write_file(filedir+"/0-question/plaintexts_json", target)

