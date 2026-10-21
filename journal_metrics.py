"""Journal metrics: official SCImago export; independently sourced JIF values."""
import csv
import io
import json
from pathlib import Path
import re
import urllib.request

# Explicit data year, never silently interpret the export as the current year.
SJR_YEAR = 2024
SJR_URL = f'https://www.scimagojr.com/journalrank.php?year={SJR_YEAR}&out=xls'
SNAPSHOT = Path('scimago.json')


def normalize_issn(value):
    value = re.sub(r'[^0-9X]', '', str(value).upper())
    return value if len(value) == 8 else None


def parse_export(text):
    rows = csv.DictReader(io.StringIO(text.lstrip('\ufeff')), delimiter=';')
    required = {'Title', 'Issn', 'SJR Best Quartile', 'Categories'}
    if not required.issubset(rows.fieldnames or []):
        raise ValueError('SCImago export schema not recognized')
    entries = []
    for row in rows:
        if row.get('Type', 'journal') != 'journal':
            continue
        issns = [normalize_issn(s) for s in row['Issn'].split(',')]
        issns = [s for s in issns if s]
        # Export includes quartiles per category, not just Best Quartile.
        categories = [{'name': name.strip(), 'quartile': quartile}
                      for name, quartile in re.findall(r'([^;]+?)\s*\((Q[1-4])\)', row['Categories'])]
        if not issns or not categories:
            continue
        entries.append({'title': row['Title'], 'issns': issns, 'year': SJR_YEAR,
                        'categories': categories, 'source': SJR_URL})
    if len(entries) < 1000:
        raise ValueError('SCImago export is incomplete')
    return entries


def download():
    req = urllib.request.Request(SJR_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        entries = parse_export(response.read().decode('utf-8-sig'))
    SNAPSHOT.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
    print(f'Saved {len(entries)} journal records, SCImago {SJR_YEAR}.')


def load_index():
    entries = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    index = {}
    for record in entries:
        for issn in record['issns']:
            index.setdefault(issn, []).append(record)
    return index


def match_journal(paper, index):
    journal = paper.get('journalInfo', {}).get('journal', {})
    identifiers = {normalize_issn(journal.get(field, '')) for field in ('issn', 'essn')}
    records = {}
    for identifier in identifiers - {None}:
        for record in index.get(identifier, []):
            records[record['title']] = record
    if len(records) != 1:
        return None  # Missing or conflicting ISSNs: never guess from title.
    record = next(iter(records.values()))
    # Use the best quartile among explicitly relevant categories.
    relevant = [c for c in record['categories'] if re.search(
        r'genetic|molecular|medicine|oncology|cancer|immunolog|biotech|biochem|'
        r'cell biology|drug discovery|pharmacolog|multidisciplinary', c['name'], re.I)
        and c['quartile'] in ('Q1', 'Q2')]
    if not relevant:
        return None
    category = min(relevant, key=lambda c: (c['quartile'], c['name']))
    return {**record, 'category': category['name'], 'quartile': category['quartile']}


def jif_for(paper):
    data = json.loads(Path('impact_factors.json').read_text(encoding='utf-8'))
    journal = paper.get('journalInfo', {}).get('journal', {})
    identifiers = {normalize_issn(journal.get(field, '')) for field in ('issn', 'essn')}
    matches = [record for record in data if identifiers.intersection(record['issns'])]
    return max(matches, key=lambda record: record['year']) if matches else None


if __name__ == '__main__':
    download()
