import datetime as dt
import unittest
from digest import select, render, summarize


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

    def test_summary_prefers_results_and_preserves_caution(self):
        paper = {'abstractText': '<h4>BACKGROUND:</h4><p>Old context.</p><h4>RESULTS:</h4><p>Treatment may help in mice. Human efficacy remains unknown.</p>'}
        text = summarize(paper)
        self.assertIn('may help in mice', text)
        self.assertIn('Human efficacy remains unknown.', text)
        self.assertNotIn('Old context', text)
        self.assertNotIn('<p>', text)

    def test_missing_abstract_is_explicit(self):
        self.assertIn('unavailable', summarize({}))

    def test_summary_and_digest_size(self):
        import html
        import re
        paper = {'doi': '10.1/test', 'title': 'Title ' * 200,
                 'journalTitle': 'Journal ' * 100,
                 'abstractText': 'Background sentence. ' + 'Result word ' * 300 + '.'}
        paper['metrics'] = {'source': 'https://www.scimagojr.com/', 'year': 2024,
                            'quartile': 'Q2', 'category': 'Genetics (clinical)'}
        self.assertLessEqual(len(summarize(paper)), 320)
        text = render([('Medical genetics', 'Recent research', paper)] * 5, dt.date(2026, 10, 22))
        visible = html.unescape(re.sub('<[^>]+>', '', text))
        self.assertLessEqual(len(visible.encode('utf-16-le')) // 2, 4096)
        self.assertEqual(text.count('<b>Abstract highlights:</b>'), 5)


if __name__ == '__main__':
    unittest.main()
