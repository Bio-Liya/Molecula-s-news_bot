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

TOPICS = {
    'Medical genetics': '"medical genetics" OR "genomic medicine" OR "rare disease"',
    'Sequencing': '"clinical sequencing" OR "long read sequencing" OR "whole genome sequencing"',
    'Liquid biopsy': '"liquid biopsy" OR "circulating tumor DNA"',
    'Epigenetics': '"epigenetic therapy" OR "DNA methylation"',
    'Gene therapy': '"gene therapy" OR "genome editing"',
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


def select(fetch, seen, today):
    chosen, used = [], set(seen)
    topics = list(TOPICS)
    offset = today.toordinal() % len(topics)
    topics = topics[offset:] + topics[:offset]
    for days, label in ((3, 'Recent research'), (90, 'Trend watch')):
        for topic in topics:
            for paper in fetch(topic, days, today):
                if not paper.get('doi') or not paper.get('title'):
                    continue
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


def render(items, today):
    lines = [f'<b>Molecula | {today.isoformat()}</b>',
             'Research digest · English · primary papers', '']
    if not items:
        lines.append('No new eligible primary papers found in the past 90 days. No older items repeated.')
    for topic, label, paper in items:
        title = re.sub('<[^>]+>', '', html.unescape(paper['title']))[:320]
        doi = urllib.parse.quote(paper['doi'], safe='/')
        lines.extend([f'<b>{html.escape(topic)} · {label}</b>', html.escape(title),
                      html.escape(f"{paper.get('journalTitle', 'Journal')} · {paper.get('firstPublicationDate', paper.get('pubYear', ''))}"),
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
    items = select(search, state['seen'], today)
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
