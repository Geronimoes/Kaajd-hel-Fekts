# AGENTS.md

This file gives coding agents current project context for Kaajd.

## What this is

Kaajd is a WhatsApp chat export analyzer with:

- CLI analysis (`cli.py`)
- Flask web app (`wa-flask.py` for local compatibility, `wsgi:app` for production)

The app parses `.txt` exports, persists data in SQLite, computes analytics, and serves both static and interactive dashboard outputs.

## Current architecture

Core modules:

- `app/parser.py` - multi-format WhatsApp parser + enrichment flags
- `app/analyzer.py` - summary stats + output writing + DB persistence/cache reuse
- `app/database.py` - SQLite schema/helpers (`chats`, `messages`, `stats`)
- `app/analyzers/` - advanced analytics (`response_patterns`, `media_links`, `topics`, `relationships`)
- `app/charts_payloads.py` - Plotly-oriented API payload shaping
- `app/routes.py` - Flask routes and JSON API endpoints

Web templates:

- `app/templates/upload.html`
- `app/templates/dashboard.html` (interactive tabbed dashboard)

Upload flow notes:

- `POST /` now supports both normal form posts and AJAX uploads (`X-Requested-With: XMLHttpRequest`) with JSON error/redirect responses for improved client-side error handling.

Bundled demo data:

- `data/sample-chat.txt` (used by `GET /demo` for one-click onboarding)

## Main entry points

Preferred:

```bash
python3 cli.py /path/to/chat.txt
python3 wa-flask.py
```

Production web:

```bash
gunicorn wsgi:app
```

Compatibility wrappers (deprecated but still present):

- `wa-stats.py`
- `wa-stats-flask.py`
- `wa-graphs.py`
- `wa-flask.py`

## Fast verification

Run the consolidated local checks:

```bash
./scripts/dev-check.sh
```

This verifies parser smoke tests, CLI run, cache reuse, and API endpoints.

## API surface (current)

- `GET /api/chat/<chat_id>/context`
- `GET /api/chat/<chat_id>/messages`
- `GET /api/chat/<chat_id>/response-patterns`
- `GET /api/chat/<chat_id>/media-links`
- `GET /api/chat/<chat_id>/topics`
- `GET /api/chat/<chat_id>/relationships`
- `GET /api/chat/<chat_id>/dashboard-data`
- `GET /api/chats`

## Deployment

Docker files are present:

- `Dockerfile`
- `docker-compose.yml`
- `.env.example`

Basic auth is env-driven (`KAAJD_AUTH_ENABLED`, username/password vars).

## Practical notes for agents

- Keep `CHANGELOG.md` and `TODO.md` updated as work progresses.
- Prefer extending `cli.py`/`app/*` over legacy wrapper scripts.
- Preserve compatibility wrappers until removal is explicitly requested.
