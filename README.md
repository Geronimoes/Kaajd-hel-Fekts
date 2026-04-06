# Kaajd

Kaajd is a WhatsApp chat export analyzer. It parses `.txt` exports, generates per-person stats, and builds charts for activity and message patterns.

## Current status

The project is in an active refactor:

- Phase 1/2 core migration is completed in practice (modular app, parser/data layer, SQLite, cache reuse).
- Phase 3 analyzers are implemented: response patterns, media/links, topics, and relationships.
- Phase 4 interactive dashboard is live with Plotly tabs, filters, loading/error states, and browser cache fallback.
- Legacy scripts (`wa-stats.py`, `wa-graphs.py`, `wa-flask.py`) remain as deprecated compatibility wrappers.
- Phase 5 deployment baseline is in place (Docker, gunicorn, env-driven auth, health checks).

## Project structure

```text
kaajd/
  app/
    __init__.py
    analyzer.py
    database.py
    graphs.py
    parser.py
    routes.py
    static/
      css/
      uploads/
    templates/
      base.html
      dashboard.html
      upload.html
  cli.py
  config.py
  requirements.txt
  wa-flask.py
  wa-graphs.py
  wa-stats.py
  wa-stats-flask.py
```

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Developer workflow

Use the local venv for all development commands:

```bash
source .venv/bin/activate
```

Run the one-shot local verification script:

```bash
./scripts/dev-check.sh
```

This runs parser smoke tests, full CLI analysis on `data/chat.txt`, cache reuse checks, and API endpoint sanity checks.

For next-session continuity, see `SESSION_HANDOFF.md`.

If you use the word cloud and NLTK stopwords for the first time:

```python
import nltk
nltk.download("stopwords")
```

## Usage

### New CLI entry point

```bash
python3 cli.py /path/to/chat.txt
```

This generates:

- `raw-data.csv`
- `summary.html`
- `summary.json`
- graph PNG files

It also stores parsed data and summary stats in SQLite (`kaajd.sqlite3` by default).

Output is written to:

```text
<input_dir>/<chat_filename_without_ext>/output/
```

### Web app

```bash
python3 wa-flask.py
```

Then open:

- `http://localhost:5000`

On the upload page you can also use **Try with demo data**, which analyzes the bundled `data/sample-chat.txt` file through `GET /demo` and redirects to results.

### Legacy script compatibility

These still work and route into the refactored code:

```bash
python3 wa-stats.py /path/to/chat.txt
python3 wa-graphs.py /path/to/chat.txt
python3 wa-stats-flask.py /path/to/chat.txt
```

## Parser notes

The parser now supports multiple WhatsApp export formats and auto-detects the most likely line format from the first few message lines.

Message enrichment fields in `raw-data.csv`:

- `IsSystemMessage`
- `IsMediaMessage`
- `HasLink`

Language detection uses `langdetect` when installed; otherwise it falls back to `unknown`.

## SQLite data layer

The app now persists analysis data to SQLite with these tables:

- `chats`
- `messages`
- `stats`

Default database path:

- `./kaajd.sqlite3`

Note: local DB and chat test data paths are gitignored by default, except the bundled `data/sample-chat.txt` demo dataset.

Override with:

- `KAAJD_DB_PATH=/custom/path/kaajd.sqlite3`

`cli.py` also accepts:

```bash
python3 cli.py /path/to/chat.txt --db-path /custom/path/kaajd.sqlite3
```

## Parser smoke test

Run the basic parser format smoke test:

```bash
python3 parser_smoke_test.py
```

This checks that known sample lines are auto-detected into the expected parser formats.

## API

Initial context endpoint for future LLM integrations:

```text
GET /api/chat/<chat_id>/context
```

Returns chat metadata, aggregate totals, and top participants from SQLite.

Message retrieval endpoint (DB-backed):

```text
GET /api/chat/<chat_id>/messages
```

Supported query params:

- `person`
- `has_link` (`true`/`false`)
- `is_media_message` (`true`/`false`)
- `limit`
- `offset`

Response pattern analysis endpoint (DB-backed):

```text
GET /api/chat/<chat_id>/response-patterns
```

Returns:

- Average response times between sender pairs
- Reply transition matrix (`who replies to whom`)
- Conversation starter breakdown with first-response metrics

Media/link analysis endpoint (DB-backed):

```text
GET /api/chat/<chat_id>/media-links
```

Returns:

- Per-person media/link counts and media-to-text ratio
- Monthly breakdown by participant
- Top shared domains

Topic analysis endpoint (DB-backed):

```text
GET /api/chat/<chat_id>/topics
```

Query params:

- `max_topics` (optional, default `5`, range `2-10`)

Returns:

- Monthly TF-IDF term trends
- NMF topic clusters with top terms and top months

Relationship dynamics endpoint (DB-backed):

```text
GET /api/chat/<chat_id>/relationships
```

Returns:

- Affinity scores derived from reply transition ratios
- Pairwise daily activity correlations (Pearson)
- Two-person chat balance metrics (initiative and response-time asymmetry)

Dashboard data endpoint (Phase 4 prep):

```text
GET /api/chat/<chat_id>/dashboard-data
```

Returns:

- Combined analysis payloads (response/media/topics/relationships)
- Plotly-oriented data structures ready for interactive charts

The `/results/<analysis_id>` page now uses this endpoint to render an interactive tabbed dashboard with person and date-range filters, while keeping a static-graph fallback tab.
The dashboard now includes loading and error states, and caches the latest dashboard payload in browser session storage for faster reloads.
Interactive charts include one-click PNG download buttons, and the Static Graphs tab now exposes explicit `Download PNG` links for each image.

Recent analyses endpoint:

```text
GET /api/chats
```

Returns recently stored analyses from SQLite (default limit 10), including source filename, timestamps, message count, language, and derived `analysis_id` values suitable for reopening existing sessions.

## Deployment (Docker)

Build and run with Docker Compose:

```bash
cp .env.example .env
# edit credentials in .env first
docker compose up --build
```

Kaajd is served on `http://localhost:5000`.

### Optional Basic Auth

Set these environment variables (for example in `docker-compose.yml`):

- `KAAJD_AUTH_ENABLED=true`
- `KAAJD_BASIC_AUTH_USERNAME=your-user`
- `KAAJD_BASIC_AUTH_PASSWORD=your-password`

When enabled, all app and API routes require HTTP Basic Auth.

### Mobile access over Tailscale

For testing from mobile over your Tailnet:

1. Run Kaajd on a Tailscale-connected machine.
2. Keep Basic Auth enabled (`KAAJD_AUTH_ENABLED=true`).
3. Open `http://<tailscale-hostname-or-ip>:5000` on your phone/tablet.
4. Log in with `KAAJD_BASIC_AUTH_USERNAME` and `KAAJD_BASIC_AUTH_PASSWORD`.

Tip: verify local access first at `http://127.0.0.1:5000`.

### Reverse proxy samples

See `docs/reverse-proxy.md` for Caddy/nginx examples.

## LLM integration notes

Structure-only planning notes are documented in `docs/llm-integration.md`.

## Legacy script status

Legacy entry scripts remain as compatibility shims and now print deprecation notices:

- `wa-stats.py`
- `wa-stats-flask.py`
- `wa-graphs.py`
- `wa-flask.py`

Preferred entry points are:

- `python3 cli.py <chat.txt>` for CLI
- `gunicorn wsgi:app` for production web serving

## Planned roadmap

See `PLAN.md` for the full phased roadmap.
