import unittest
from journal_metrics import match_journal, normalize_issn
from digest import select, metrics_line
import datetime as dt


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.paper = {'doi': '10.1/a', 'title': 'Paper',
                      'journalInfo': {'journal': {'essn': '1234-567X'}}}
        self.record = {'title': 'Journal', 'year': 2024, 'source': 'https://www.scimagojr.com/',
                       'issns': ['1234567X'], 'categories': [
                           {'name': 'Genetics', 'quartile': 'Q2'},
                           {'name': 'Economics', 'quartile': 'Q1'}]}
        self.index = {'1234567X': [self.record]}

    def test_relevant_category_not_best_unrelated_quartile(self):
        result = match_journal(self.paper, self.index)
        self.assertEqual(result['quartile'], 'Q2')
        self.assertEqual(result['category'], 'Genetics')

    def test_reject_missing_q3_q4_and_ambiguous(self):
        self.assertIsNone(match_journal({}, self.index))
        for quartile in ('Q3', 'Q4'):
            self.record['categories'] = [{'name': 'Genetics', 'quartile': quartile}]
            self.assertIsNone(match_journal(self.paper, self.index))
        self.index['1234567X'].append({**self.record, 'title': 'Other journal'})
        self.assertIsNone(match_journal(self.paper, self.index))

    def test_filter_applies_to_recent_and_trends(self):
        self.record['categories'] = [{'name': 'Genetics', 'quartile': 'Q3'}]
        items = select(lambda *args: [self.paper], [], dt.date(2026, 10, 22), self.index)
        self.assertEqual(items, [])

    def test_jif_is_not_invented_or_replaced_by_sjr(self):
        line = metrics_line({'metrics': {**self.record, 'quartile': 'Q2', 'category': 'Genetics'}})
        self.assertIn('JIF unavailable', line)
        self.assertIn('SCImago 2024: Q2', line)
        self.assertEqual(normalize_issn('1234-567x'), '1234567X')
