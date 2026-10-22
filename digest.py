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
PRIORITY_TIERS = (
    ('Liquid biopsy', 'Medical genetics', 'mRNA vaccines', 'ML in biology'),
    ('Bioinformatics', 'Gene therapy', 'Sequencing', 'RNA-seq'),
    ('Epigenetics', 'CRISPR-Cas', 'Molecular cloning'),
)
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
    topics = [topic for tier in PRIORITY_TIERS for topic in tier]
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


# Countries are institutional affiliations, not author nationality or publisher country.
# Only explicit country names at the end of affiliation addresses are recognized.
COUNTRY_NAMES = (
    'Afghanistan|Albania|Algeria|Andorra|Angola|Argentina|Armenia|Australia|Austria|'
    'Azerbaijan|Bahrain|Bangladesh|Belarus|Belgium|Belize|Benin|Bhutan|Bolivia|'
    'Bosnia and Herzegovina|Botswana|Brazil|Brunei|Bulgaria|Burkina Faso|Burundi|'
    'Cambodia|Cameroon|Canada|Chile|China|Colombia|Costa Rica|Croatia|Cuba|Cyprus|'
    'Czechia|Denmark|Dominican Republic|Ecuador|Egypt|El Salvador|Estonia|Ethiopia|'
    'Fiji|Finland|France|Gabon|Gambia|Germany|Ghana|Greece|Guatemala|Haiti|Honduras|'
    'Hungary|Iceland|India|Indonesia|Iran|Iraq|Ireland|Israel|Italy|Jamaica|Japan|'
    'Jordan|Kazakhstan|Kenya|Kuwait|Kyrgyzstan|Laos|Latvia|Lebanon|Libya|Lithuania|'
    'Luxembourg|Madagascar|Malawi|Malaysia|Maldives|Mali|Malta|Mauritius|Mexico|'
    'Moldova|Monaco|Mongolia|Montenegro|Morocco|Mozambique|Myanmar|Namibia|Nepal|'
    'Netherlands|New Zealand|Nicaragua|Niger|Nigeria|North Macedonia|Norway|Oman|'
    'Pakistan|Palestine|Panama|Paraguay|Peru|Philippines|Poland|Portugal|Qatar|'
    'Romania|Russia|Rwanda|Saudi Arabia|Senegal|Serbia|Singapore|Slovakia|Slovenia|'
    'Somalia|South Africa|South Korea|South Sudan|Spain|Sri Lanka|Sudan|Sweden|'
    'Switzerland|Syria|Taiwan|Tanzania|Thailand|Tunisia|Turkey|Uganda|Ukraine|'
    'United Arab Emirates|United Kingdom|United States|Uruguay|Uzbekistan|'
    'Venezuela|Vietnam|Yemen|Zambia|Zimbabwe'
).split('|')
COUNTRY_ALIASES = {name.casefold(): name for name in COUNTRY_NAMES}
COUNTRY_ALIASES.update({
    'usa': 'United States', 'u.s.a.': 'United States', 'us': 'United States',
    'united states of america': 'United States',
    'uk': 'United Kingdom', 'u.k.': 'United Kingdom',
    'england': 'United Kingdom', 'scotland': 'United Kingdom',
    'wales': 'United Kingdom', 'northern ireland': 'United Kingdom',
    'pr china': 'China', 'p.r. china': 'China', 'p. r. china': 'China',
    "people's republic of china": 'China',
    'republic of korea': 'South Korea', 'korea': 'South Korea',
    'russian federation': 'Russia', 'czech republic': 'Czechia',
    'the netherlands': 'Netherlands', 'türkiye': 'Turkey',
    'viet nam': 'Vietnam', 'islamic republic of iran': 'Iran',
})


def author_countries(paper):
    countries = set()
    authors = paper.get('authorList', {}).get('author', [])
    affiliations = []
    for author in authors:
        affiliations.extend(author.get('authorAffiliationDetailsList', {}).get('authorAffiliation', []))
    if paper.get('firstAuthorAffiliation'):
        affiliations.append({'affiliation': paper['firstAuthorAffiliation']})
    for affiliation in affiliations:
        explicit = plain_text(affiliation.get('country', '')).strip(' .').casefold()
        if explicit in COUNTRY_ALIASES:
            countries.add(COUNTRY_ALIASES[explicit])
            continue
        address = plain_text(affiliation.get('affiliation', ''))
        # Email domains and journal metadata are never used to infer geography.
        address = re.split(r'\b(?:Electronic address|E-?mail)\s*:', address, flags=re.I)[0]
        address = re.sub(r'\S+@\S+', '', address).strip(' .;')
        tail = re.split(r'[,;]', address)[-1].strip(' .').casefold()
        if tail in COUNTRY_ALIASES:
            countries.add(COUNTRY_ALIASES[tail])
    return sorted(countries)


def article_links(paper):
    doi = urllib.parse.quote(paper['doi'], safe='/')
    parts = [f'<a href="https://doi.org/{doi}">Publication</a>']
    jif = paper.get('jif')
    if jif:
        parts.append(f'<a href="{html.escape(jif["source"], quote=True)}">JIF {html.escape(str(jif["value"]))} ({jif["year"]})</a>')
    countries = author_countries(paper)
    parts.append(html.escape(shorten(', '.join(countries), 130)) if countries else 'Countries not reported')
    return ' · '.join(parts)


def render(items, today):
    lines = [f'<b>Research digest {today.strftime("%d.%m.%Y")}</b>', '']
    if not items:
        lines.append('No new papers to share today.')
    for _, _, paper in items:
        lines.extend([f'<b>{html.escape(shorten(plain_text(paper["title"]), 240))}</b>',
                      html.escape(summarize(paper)),
                      article_links(paper), ''])
    return '\n'.join(lines).rstrip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--manual', action='store_true', help='Manual delivery; does not consume the scheduled daily slot')
    args = parser.parse_args()
    today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=3)).date()
    state = json.loads(STATE.read_text()) if STATE.exists() else {'seen': [], 'last_date': None}
    delivery_key = 'last_manual_date' if args.manual else 'last_scheduled_date'
    if state.get(delivery_key) == str(today) and not args.dry_run:
        print('Already sent today for this delivery mode.')
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
    state[delivery_key] = str(today)
    state['seen'] = (state['seen'] + [key(p) for _, _, p in items])[-2000:]
    STATE.write_text(json.dumps(state, indent=2))
    print(f'Sent {len(items)} papers.')


if __name__ == '__main__':
    main()
