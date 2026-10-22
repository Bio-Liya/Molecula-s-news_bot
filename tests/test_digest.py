import datetime as dt
import unittest
from digest import select, render, summarize, TOPICS, PRIORITY_TIERS, author_countries


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
        self.assertEqual(len(select(fetch, seen, dt.date(2026, 10, 22))), 5)
        all_seen = [('10.1/' + topic).lower() for topic in TOPICS]
        self.assertEqual(select(fetch, all_seen, dt.date(2026, 10, 22)), [])

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
        self.assertEqual(text.count('>Publication</a>'), 5)

    def test_priority_order_is_stable_across_days(self):
        expected = ['Liquid biopsy', 'Medical genetics', 'mRNA vaccines',
                    'ML in biology', 'Bioinformatics']
        for day in (22, 23):
            items = select(lambda topic, *args: [{'doi': '10.1/' + topic, 'title': topic}],
                           [], dt.date(2026, 10, day))
            self.assertEqual([topic for topic, _, _ in items], expected)
        configured = [topic for tier in PRIORITY_TIERS for topic in tier]
        self.assertEqual(len(configured), len(set(configured)))
        self.assertEqual(set(configured), set(TOPICS))

    def test_missing_high_priority_topics_fall_through(self):
        available = {'ML in biology', 'Gene therapy', 'RNA-seq', 'Epigenetics', 'Molecular cloning'}
        def fetch(topic, days, today):
            return [{'doi': '10.1/' + topic, 'title': topic}] if topic in available else []
        items = select(fetch, [], dt.date(2026, 10, 22))
        self.assertEqual([topic for topic, _, _ in items],
                         ['ML in biology', 'Gene therapy', 'RNA-seq', 'Epigenetics', 'Molecular cloning'])

    def test_trend_watch_keeps_priority_order(self):
        def fetch(topic, days, today):
            return [] if days == 3 else [{'doi': '10.1/' + topic, 'title': topic}]
        items = select(fetch, [], dt.date(2026, 10, 22))
        self.assertEqual([topic for topic, _, _ in items],
                         ['Liquid biopsy', 'Medical genetics', 'mRNA vaccines', 'ML in biology', 'Bioinformatics'])
        self.assertTrue(all(label == 'Trend watch' for _, label, _ in items))

    def test_clean_layout_and_optional_jif(self):
        paper = {'title': 'A study', 'doi': '10.1/test',
                 'abstractText': 'A finding.',
                 'authorList': {'author': [{'authorAffiliationDetailsList': {
                     'authorAffiliation': [{'affiliation': 'Institute, London, UK.'}]}}]}}
        text = render([('Liquid biopsy', 'Recent research', paper)], dt.date(2026, 10, 22))
        self.assertTrue(text.startswith('<b>Research digest 22.10.2026</b>'))
        for unwanted in ('Liquid biopsy', 'Recent research', 'SCImago', 'English',
                         'Abstract highlights', 'JIF unavailable', 'clinical advice'):
            self.assertNotIn(unwanted, text)
        self.assertIn('United Kingdom', text)
        self.assertNotIn('JIF', text)
        paper['jif'] = {'value': '4.9', 'year': 2025, 'source': 'https://www.nature.com/srep/about'}
        self.assertIn('JIF 4.9 (2025)', render([('', '', paper)], dt.date(2026, 10, 22)))

    def test_multiple_author_countries_and_unknown(self):
        def affiliation(address):
            return {'authorAffiliationDetailsList': {'authorAffiliation': [{'affiliation': address}]}}
        paper = {'authorList': {'author': [
            affiliation('Institute, Boston, MA, USA. Electronic address: name@example.fr'),
            affiliation('Institute, Berlin, Germany.'),
            affiliation('Institute, London, United Kingdom.'),
            affiliation('Another Institute, USA.')]}}
        self.assertEqual(author_countries(paper), ['Germany', 'United Kingdom', 'United States'])
        self.assertEqual(author_countries({'journalInfo': {'country': 'France'}}), [])
        self.assertEqual(author_countries({'firstAuthorAffiliation': 'Unknown Institute name@example.de'}), [])
        self.assertIn('Countries not reported',
                      render([('', '', {'title': 'Study', 'doi': '10.1/x'})], dt.date(2026, 10, 22)))


if __name__ == '__main__':
    unittest.main()
