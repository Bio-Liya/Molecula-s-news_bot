# Molecula's news bot

Free English Telegram literature digest covering medical genetics, sequencing,
liquid biopsy, epigenetics, gene therapy, mRNA vaccines, RNA-seq,
bioinformatics, ML in biology (machine learning, deep learning and foundation
models for genomics, transcriptomics, proteomics, protein design and drug discovery),
CRISPR-Cas and molecular cloning technologies (Gibson Assembly,
Golden Gate and DNA assembly). Topic priority rotates daily; five papers cannot
cover all eleven topics in every edition.

## Activate

1. Create a Telegram bot with @BotFather. Open its private chat and press Start,
   or add it to your channel with permission to post.
2. In Settings → Secrets and variables → Actions add `TELEGRAM_BOT_TOKEN`
   and `TELEGRAM_CHAT_ID` (numeric private chat ID or `@channelusername`).
   Never commit tokens. For a private chat, obtain its ID from Telegram's
   Bot API getUpdates after messaging the bot; keep the token out of shared logs.
3. Under Actions → Daily Telegram digest → Run workflow, leave `send` false
   for a preview. Then run with `send` true for a delivery test.
4. Automatic delivery is scheduled daily at 06:07 UTC / 09:07 Moscow.
   GitHub can delay scheduled jobs; this is not an exact-time scheduler.

## Content and cost

Europe PMC's free API supplies English PubMed-indexed papers with DOIs.
Up to five papers, rotating topic priority daily. First look back three days;
if fewer than three items qualify, fill from the past 90 days, labeled Trend
watch. Reviews, meta-analyses, editorials and comments are excluded. Publication
type metadata is imperfect, so this filter cannot guarantee study design.
Each item has the original title, journal/date and a DOI link to the publisher.
Each item includes a short English extractive summary (Abstract highlights), up to
260 displayed characters, taken from the authors' abstract supplied by Europe PMC. Structured
abstracts prioritize results/conclusions; unstructured abstracts use the opening
and closing sentences. Long extracts are shortened with an ellipsis. This is an
automatic excerpt, not a full-text analysis or an AI rewrite. Missing abstracts
are explicitly marked; no claims are inferred from titles. Trend watch is
recent research discovery, not a statistically measured trend ranking.
No fabricated news, no repeat DOIs while retained in the last 2,000-item history.
If all sources fail the job fails instead of reporting a quiet day.

No LLM, paid APIs, server, dependency packages, cache or stored artifacts.
Standard GitHub-hosted runners are free for this public repository under
GitHub's current billing policy. Expected operating cost: 0 RUB/month.
Recheck billing if changing visibility or runner type.

Delivery history is committed to state.json only after Telegram confirms
success. Concurrent jobs are serialized and same-day reruns skip delivery.
If sending succeeds but saving history fails, manual reruns may duplicate the
message: check Telegram first. Uncertain sends are not automatically retried.
Public repository schedules may be disabled after 60 days without activity;
successful daily history commits normally provide activity. Monitor Actions
failures and re-enable schedules if disabled.

## Local checks

Python 3.12+, no packages required:

```sh
python -m unittest discover -s tests -v
python digest.py --dry-run
```

Sources: https://europepmc.org/RestfulWebService
and https://docs.github.com/en/billing/concepts/product-billing/github-actions


## SCImago Q1–Q2 filter

The digest implements a strict ISSN match and admits Q1/Q2 in
a relevant subject category, including multidisciplinary journals. Unknown,
ambiguous, Q3/Q4, or unrelated-category matches are excluded, also in Trend watch.
The chosen category, quartile and data year appear beside each article.
This is a journal-level filter, not an assessment of an individual study.

SCImago's official export rejects automated downloads from Actions (HTTP 403).
The daily workflow uses the checked-in validated snapshot scimago.json.gz.
Imported 29,381 journal records from the user-supplied 2024 official CSV on
2026-10-22. Source CSV SHA-256:
5054289ee269d611a63322bcc71226e8430b43e8535a1fd4577b630af5a5bd18.
Every record retains its source URL, year and category quartiles.

To import the official 2024 SCImago export:
1. Open https://www.scimagojr.com/journalrank.php?year=2024 and use Download data.
2. Keep the file unchanged; it is a semicolon-delimited CSV despite the xls URL.
3. Run: python journal_metrics.py path/to/scimagojr_2024.csv
4. Commit scimago.json.gz and run the workflow in preview mode before enabling.
The importer validates the schema and at least 1,000 journals. Only explicit
category quartiles are used. The year is pinned to 2024; importing another year's
data requires updating SJR_YEAR and the snapshot together. Check SCImago annually
and refresh from the newest available official export; never relabel an older
snapshot as current. No runtime dependency on SCImago or a paid service.

Journal Impact Factor (JIF) is separate from SJR and Cites/Doc. Public journal
pages sometimes disclose it; Clarivate's complete Journals API requires a
subscription. impact_factors.json stores verified values with ISSNs, metric year,
publisher source URL and verification date. Coverage is currently limited to
Scientific Reports; other journals explicitly show JIF unavailable, meaning no
verified value in our dataset, not that the journal has no JIF. Add entries only
after verifying a publisher or Clarivate source. No inferred or fabricated JIFs.
Source: https://developer.clarivate.com/apis/wos-journal
