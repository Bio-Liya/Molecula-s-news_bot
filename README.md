# Molecula's news bot

Free English Telegram literature digest covering medical genetics, sequencing,
liquid biopsy, epigenetics, gene therapy and mRNA vaccines.

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
320 characters, taken from the authors' abstract supplied by Europe PMC. Structured
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

