# NY Apartment Finder (scraper)

This repository contains a simple framework to scrape apartment listings
and notify when new listings appear. It's designed to run in GitHub
Actions on a schedule.

Quick start

- (Optional) run locally with a virtualenv and the `.env` file:

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python scraper.py
  ```

Files of interest

- `scrapers/`: individual site scrapers. Add modules exposing `scrape()`.
- `storage.py`: persists seen listing ids in `./data/seen.json`.
- `notifier.py`: posts to Telegram or prints as fallback. Notifications now include a `source` tag so you can tell which scraper produced the listing.
- `.github/workflows/scrape.yml`: runs `python scraper.py` on a schedule.

Extending

- Add new scraper modules under `scrapers/` returning list of dicts
  with at least `id`, `title`, and `url` keys.
- Customize `notifier.py` to add email or SMS providers.

Filtering
 
You can filter which listings trigger notifications using environment variables:

- `FILTER_MIN_BEDS`: minimum number of bedrooms (integer).
- `FILTER_MAX_PRICE`: maximum price in USD (integer).
- `FILTER_BOROUGHS`: comma-separated borough names or keywords (case-insensitive).

Filters are applied before notifications; only listings that pass filters are marked as seen so you can tune filters without losing items you skipped.

Telegram (recommended, free)

- Create a bot with `@BotFather` in Telegram and copy the bot token (`TELEGRAM_BOT_TOKEN`).
- Get your chat id:
  1. Open Telegram and search for `@userinfobot` (a helper bot).
  2. Start a chat with `@userinfobot` and it will respond with your user ID (chat ID).
  3. Or, start a chat with your bot, send a message, then visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser to see your chat ID in the JSON response.
- Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as environment variables (or GitHub secrets) and the scraper will send one Telegram message per new listing.

Example quick test (bash):

```bash
export TELEGRAM_BOT_TOKEN="<your token>"
export TELEGRAM_CHAT_ID="<your chat id>"
python - <<'PY'
from notifier import notify
notify([{"id":"x","title":"Test apt","url":"https://example.com","price":"$1000","excerpt":"Quick test","source":"residenewyork"}])
PY
```

Airtable form integration (no API access)

If you only have access to the Airtable form URL (not a shared view or API),
you can still detect new/removed unit options by collecting the dropdown list
in the browser and passing it to the scraper.

1) Start the local receiver (writes a JSON snapshot used by the scraper):

```bash
python scripts/airtable_form_receiver.py
```

2) Install the Tampermonkey userscript:

- File: `scripts/airtable_form_collector.user.js`
- In Tampermonkey, create a new script, paste the file contents, save.
- Visit the Airtable form page and it will collect dropdown options and
  POST to `http://127.0.0.1:8765/airtable-form`.

3) Run the scraper (it will also read `data/airtable_form_snapshot.json`):

```bash
python scraper.py
```

Notes
- The form only exposes option text; it does not include full listing details.
- To avoid double notifications, the scraper deduplicates by a canonical
  key derived from URL or normalized title.


