import datetime as dt
import unittest
from digest import select, render


class DigestTests(unittest.TestCase):
    def test_fallback_and_duplicate_filter(self):
        calls = []
        def fetch(topic, days, today):
            calls.append(days)
            return [] if days == 3 else [{'doi': '10.1/' + topic, 'title': topic}]
        items = select(fetch, [], dt.date(2026, 10, 22))
        self.assertEqual(len(items), 5)
        self.assertTrue(all(label == 'Trend watch' for _, label, _ in items))
        self.assertIn(90, calls)
        seen = [p['doi'].lower() for _, _, p in items]
        self.assertEqual(len(select(fetch, seen, dt.date(2026, 10, 22))), 1)

    def test_escape_and_link(self):
        text = render([('Gene therapy', 'Recent research', {'title': 'A & B <i>test</i>',
                       'doi': '10.123/a', 'journalTitle': 'A < B'})], dt.date(2026, 10, 22))
        self.assertIn('A &amp; B test', text)
        self.assertIn('https://doi.org/10.123/a', text)
        self.assertNotIn('<i>', text)


if __name__ == '__main__':
    unittest.main()
