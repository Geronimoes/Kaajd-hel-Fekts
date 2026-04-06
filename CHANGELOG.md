# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- Introduced modular app layout under `app/` with `parser.py`, `analyzer.py`, `graphs.py`, `routes.py`, and app factory in `app/__init__.py`.
- Added new CLI entry point `cli.py` for end-to-end analysis and graph generation.
- Added `config.py` for central app configuration and upload/static directory settings.
- Added Bootstrap-based template set in `app/templates/` and stylesheet in `app/static/css/app.css`.
- Added `requirements.txt` for Python dependency management.
- Added initial parser enrichment fields in `raw-data.csv`: `IsSystemMessage`, `IsMediaMessage`, `HasLink`.
- Added automatic parser format detection for multiple WhatsApp export date/time variants.
- Added best-effort language detection support via `langdetect` with fallback to `unknown`.
- Added SQLite persistence layer in `app/database.py` with `chats`, `messages`, and `stats` tables.
- Added `query_messages(...)` helper for filtered message retrieval from SQLite.
- Added `get_chat_context(chat_id)` utility for structured DB-backed chat context retrieval.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/context`.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/messages` with filters and pagination.
- Added `scripts/dev-check.sh` to run local parser, CLI, cache, and API sanity checks in one command.
- Added `parser_smoke_test.py` for quick multi-format parser detection checks.
- Added optional HTTP Basic Auth via `flask-httpauth` in `app/auth.py` and route protection in `app/routes.py`.
- Added deployment files: `Dockerfile`, `docker-compose.yml`, `.dockerignore`, and `wsgi.py` (gunicorn entrypoint).
- Added deployment/reverse-proxy guide at `docs/reverse-proxy.md`.
- Added execution tracker `TODO.md` for current implementation status.
- Added Phase 3 response analyzer module: `app/analyzers/response_patterns.py`.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/response-patterns`.
- Added Phase 3 media/link analyzer module: `app/analyzers/media_links.py`.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/media-links`.
- Added Phase 3 topics analyzer module: `app/analyzers/topics.py` (TF-IDF + NMF).
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/topics`.
- Added Phase 3 relationships analyzer module: `app/analyzers/relationships.py`.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/relationships`.
- Added Plotly payload shaping module `app/charts_payloads.py` for dashboard-ready chart data.
- Added Flask JSON endpoint `GET /api/chat/<chat_id>/dashboard-data` with combined analytics + chart payloads.
- Added DB lookup helper `get_chat_by_output_dir(...)` for dashboard context recovery.
- Added `.env.example` for Docker/runtime configuration bootstrap.
- Added `SESSION_HANDOFF.md` with explicit resume instructions for future sessions.
- Added LLM integration planning document: `docs/llm-integration.md`.

### Changed
- Refactored web flow to call Python functions directly instead of using `subprocess.run()`.
- Replaced deprecated pandas `DataFrame.append()` usage with `pd.concat()` in chat summary construction.
- Updated legacy script files (`wa-stats.py`, `wa-stats-flask.py`, `wa-graphs.py`, `wa-flask.py`) into compatibility wrappers over refactored modules.
- Updated `README.md` to document the new architecture, usage, and migration state.
- Updated `app/analyzer.py` to persist parsed messages and stats into SQLite on analysis runs.
- Updated Flask upload flow in `app/routes.py` to pass configured DB path into analysis.
- Updated `cli.py` with optional `--db-path` argument for explicit database location.
- Updated `config.py` with `DATABASE_PATH` (`KAAJD_DB_PATH` override supported).
- Updated `README.md` with SQLite and parser smoke-test instructions.
- Updated `app/analyzer.py` with cache-aware analysis reuse by source file hash.
- Updated `.gitignore` to ignore local chat data (`/data/`), SQLite DB (`/kaajd.sqlite3`), and uploaded chat artifacts.
- Updated `README.md` with venv-based developer workflow and `./scripts/dev-check.sh` usage.
- Updated `config.py` with auth settings (`KAAJD_AUTH_ENABLED`, username/password env vars).
- Updated `README.md` with Docker deployment and Basic Auth configuration instructions.
- Updated `README.md` with response-pattern API documentation.
- Updated `scripts/dev-check.sh` to include response-pattern API validation.
- Updated `config.py` with LLM placeholder settings (`KAAJD_LLM_ENDPOINT_URL`, `KAAJD_LLM_MODEL`, `KAAJD_LLM_API_KEY`).
- Updated `README.md` with media-links API and LLM integration notes.
- Updated `scripts/dev-check.sh` to include media-links API validation.
- Updated `requirements.txt` with `scikit-learn` for topic modeling.
- Updated `README.md` with topics API documentation.
- Updated `scripts/dev-check.sh` to include topics API validation.
- Updated `README.md` with relationships API documentation.
- Updated `scripts/dev-check.sh` to include relationships API validation.
- Updated `README.md` with dashboard-data API documentation.
- Updated `scripts/dev-check.sh` to include dashboard-data payload validation.
- Updated `app/templates/dashboard.html` to render a tabbed interactive Plotly dashboard.
- Updated `app/static/css/app.css` with dashboard metric-card/chart styles.
- Updated `app/routes.py` dashboard flow to pass/resolve `chat_id` for interactive API loading.
- Updated `app/templates/dashboard.html` with chart loading/error states and sessionStorage cache fallback.
- Updated `app/static/css/app.css` with `.chart-loading` visual state styling.
- Updated `README.md` and `TODO.md` for interactive dashboard reliability improvements.
- Updated `app/templates/dashboard.html` with persisted filter preferences (localStorage) and tighter person-based cross-filtering for relationship/response heatmaps.
- Updated `app/routes.py` and `app/database.py` for date-range-aware dashboard filtering and context date bounds.
- Updated `app/templates/dashboard.html` to use API-driven date-range filters (`start_date`, `end_date`) instead of month-only client filtering.
- Updated Plotly chart layouts/tooltips for better mobile readability (legend placement + hover templates).
- Updated `README.md` and `TODO.md` to reflect date-level dashboard filtering progress.
- Updated legacy wrapper scripts to print deprecation notices and point to modern entrypoints.
- Updated Docker deployment files (`Dockerfile`, `docker-compose.yml`) with health checks and `.env`-driven runtime settings.
- Updated `README.md` with mobile-over-Tailscale deployment guidance.
- Updated `AGENTS.md` to match the current modular architecture, APIs, and workflows.
- Updated `PLAN.md` with a current progress snapshot.

### Ops
- Extracted project-root WhatsApp test archive into `data/chat.txt`.
- Removed the source zip archive after extraction.
- Created local virtual environment at `.venv` and installed dependencies from `requirements.txt`.
- Ran parser smoke test and full CLI analysis against `data/chat.txt` in the venv.
- Validated API endpoints with live Flask run: `/api/chat/1/context` and `/api/chat/1/messages`.
- Verified messages endpoint filters (`person`, `has_link`, `limit`) against real data.
- Verified analyzer cache reuse path returns stable `chat_id` and `loaded_from_cache=True` for existing source hash.
- Installed new deployment/auth dependencies in `.venv` (`flask-httpauth`, `gunicorn`).
- Re-ran `./scripts/dev-check.sh` after deployment/auth changes; all checks passed.
- Verified auth enforcement: unauthenticated API request returns 401, authenticated request returns 200.
- Installed `scikit-learn` in `.venv` and verified topic analyzer dependencies.
- Re-ran `./scripts/dev-check.sh` with topics endpoint checks; all checks passed.
- Re-ran `./scripts/dev-check.sh` with relationships endpoint checks; all checks passed.
- Re-ran `./scripts/dev-check.sh` with dashboard-data endpoint checks; all checks passed.
- Verified full end-to-end checks after interactive dashboard wiring; all checks passed.
