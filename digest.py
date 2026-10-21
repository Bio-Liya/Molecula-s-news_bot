"""Free literature digest. Python standard library only."""
import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request
from journal_metrics import load_index, match_journal, jif_for

TOPICS = {
    'Medical genetics': '"medical genetics" OR "genomic medicine" OR "rare disease"',
    'Sequencing': '"clinical sequencing" OR "long read sequencing" OR "whole genome sequencing"',
    'Liquid biopsy': '"liquid biopsy" OR "circulating tumor DNA"',
    'Epigenetics': '"epigenetic therapy" OR "DNA methylation"',
    'Gene therapy': '"gene therapy" OR "genome editing"',
    'RNA-seq': '"RNA-seq" OR "RNA sequencing" OR "single cell RNA sequencing" OR "spatial transcriptomics"',
    'ML in biology': '("machine learning" OR "deep learning" OR "foundation model" OR "foundation models") AND (biology OR biological OR genomics OR transcriptomics OR proteomics OR "protein design" OR "drug discovery")',
    'Bioinformatics': '"bioinformatics" OR "computational genomics" OR "genomic data analysis"',
    'CRISPR-Cas': '"CRISPR" OR "Cas9" OR "Cas12" OR "Cas13" OR "base editing" OR "prime editing"',
    'Molecular cloning': '"molecular cloning" OR "Gibson assembly" OR "Golden Gate assembly" OR "DNA assembly" OR "recombinational cloning"',
    'mRNA vaccines': '"mRNA vaccine" OR "mRNA vaccines"',
}
STATE = Path('state.json')


def request_json(url, data=None):
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'MoleculaNewsDigest/1.0',
        **({'Content-Type': 'application/json'} if data else {}),
    })
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)


def search(topic, days, today):
    start = today - dt.timedelta(days=days)
    query = (f'({TOPICS[topic]}) AND LANG:eng AND SRC:MED '
             f'AND FIRST_PDATE:[{start} TO {today}] '
             'AND HAS_DOI:Y NOT PUB_TYPE:"Review" '
             'NOT PUB_TYPE:"Systematic Review" NOT PUB_TYPE:"Meta-Analysis" '
             'NOT PUB_TYPE:"Editorial" NOT PUB_TYPE:"Comment"')
    params = urllib.parse.urlencode({'query': query, 'format': 'json',
                                    'resultType': 'core', 'pageSize': 30,
                                    'sort': 'FIRST_PDATE_D desc'})
    result = request_json('https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + params)
    return result['resultList']['result']


def key(paper):
    return paper['doi'].lower()


def select(fetch, seen, today, journal_index=None):
    chosen, used = [], set(seen)
    topics = list(TOPICS)
    offset = today.toordinal() % len(topics)
    topics = topics[offset:] + topics[:offset]
    for days, label in ((3, 'Recent research'), (90, 'Trend watch')):
        for topic in topics:
            for paper in fetch(topic, days, today):
                if not paper.get('doi') or not paper.get('title'):
                    continue
                if journal_index is not None:
                    metrics = match_journal(paper, journal_index)
                    if metrics is None:
                        continue
                    paper = {**paper, 'metrics': metrics, 'jif': jif_for(paper)}
                identity = key(paper)
                if identity in used:
                    continue
                used.add(identity)
                chosen.append((topic, label, paper))
                break
            if len(chosen) == 5:
                return chosen
        if len(chosen) >= 3:
            break
    return chosen



def plain_text(value):
    value = re.sub(r'</?(?:p|h[1-6]|div|br)\b[^>]*>', ' ', value or '', flags=re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', value))).strip()


def shorten(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(' ', 1)[0] + '…'


def summarize(paper):
    """Extract evidence sentences from the abstract; never invent missing facts."""
    abstract = plain_text(paper.get('abstractText'))
    if not abstract:
        return 'Abstract unavailable; open the original paper for details.'
    match = re.search(r'\b(?:RESULTS?|FINDINGS|CONCLUSIONS?|INTERPRETATION)\s*:', abstract, re.I)
    evidence = abstract[match.end():].strip() if match else abstract
    evidence = re.sub(r'\b(?:RESULTS?|FINDINGS|CONCLUSIONS?|INTERPRETATION)\s*:\s*', '', evidence, flags=re.I)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', evidence)
    selected = sentences[:2] if match else ([sentences[0], sentences[-1]] if len(sentences) > 1 else sentences)
    return shorten(' '.join(selected), 320)


def metrics_line(paper):
    metrics = paper.get('metrics')
    if not metrics:
        return ''
    source = html.escape(metrics['source'], quote=True)
    line = f'<a href="{source}">SCImago {metrics["year"]}: {metrics["quartile"]}</a>'
    line += ' · ' + html.escape(shorten(metrics['category'], 35))
    jif = paper.get('jif')
    if jif:
        line += f' · <a href="{html.escape(jif["source"], quote=True)}">JIF {jif["year"]}: {html.escape(str(jif["value"]))}</a>'
    else:
        line += ' · JIF unavailable'
    return line


def render(items, today):
    lines = [f'<b>Molecula | {today.isoformat()}</b>',
             'Research digest · English · primary papers · SCImago Q1–Q2', '']
    if not items:
        lines.append('No unseen eligible SCImago Q1–Q2 papers found in the past 90 days. No older items repeated.')
    for topic, label, paper in items:
        title = shorten(plain_text(paper['title']), 180)
        doi = urllib.parse.quote(paper['doi'], safe='/')
        lines.extend([f'<b>{html.escape(topic)} · {label}</b>', html.escape(title),
                      html.escape(shorten(plain_text(paper.get('journalTitle') or paper.get('journalInfo', {}).get('journal', {}).get('title') or 'Journal'), 80) + ' · ' + str(paper.get('firstPublicationDate', paper.get('pubYear', '')))[:10]),
                      metrics_line(paper),
                      '<b>Abstract highlights:</b> ' + html.escape(shorten(summarize(paper), 260)),
                      f'<a href="https://doi.org/{doi}">Original paper</a>', ''])
    lines.append('Trend watch uses recent papers (≤90 days), not a measured trend ranking. Research findings are not clinical advice.')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)).date()
    state = json.loads(STATE.read_text()) if STATE.exists() else {'seen': [], 'last_date': None}
    if state['last_date'] == str(today) and not args.dry_run:
        print('Already sent today.')
        return
    items = select(search, state['seen'], today, load_index())
    message = render(items, today)
    if args.dry_run:
        print(message)
        return
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        raise SystemExit('Configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as Actions secrets.')
    try:
        result = request_json(f'https://api.telegram.org/bot{token}/sendMessage', json.dumps({
            'chat_id': chat, 'text': message, 'parse_mode': 'HTML',
            'link_preview_options': {'is_disabled': True},
        }).encode())
        if not result.get('ok'):
            raise ValueError('Telegram rejected message')
    except Exception:
        # Do not print a request URL containing the bot token. No automatic send retries:
        # a timeout can mean Telegram accepted the message already.
        raise SystemExit('Telegram delivery failed or is uncertain; inspect chat before retrying.') from None
    STATE.write_text(json.dumps({'last_date': str(today),
                                 'seen': (state['seen'] + [key(p) for _, _, p in items])[-2000:]}, indent=2))
    print(f'Sent {len(items)} papers.')


if __name__ == '__main__':
    main()
