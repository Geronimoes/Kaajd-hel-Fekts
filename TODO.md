# TODO

## In Progress
- [ ] Add deployment docs for container and hosted setup hardening.
- [ ] Expand Phase 3 analysis depth (`sentiment variants`, advanced topic tuning).
- [ ] Expand Phase 4 interactive dashboard polish (cross-filtering depth, richer chart interactions).
- [ ] Decide and schedule hard removal date for deprecated `wa-*` compatibility scripts.

## Next
- [ ] Add optional dark/light theme toggle for dashboard accessibility.

## Done
- [x] Create modular app structure under `app/` with app factory.
- [x] Merge parsing/stats flow and replace deprecated pandas `append()` usage.
- [x] Convert graph generation to function-based module.
- [x] Replace Flask subprocess flow with direct Python imports.
- [x] Add parser enhancements: format auto-detect, system/media/link flags, language detection.
- [x] Add SQLite layer (`chats`, `messages`, `stats`) and cache-aware analysis reuse by source hash.
- [x] Add API endpoints: `/api/chat/<id>/context` and `/api/chat/<id>/messages`.
- [x] Add local test data setup, parser smoke test, and consolidated `scripts/dev-check.sh`.
- [x] Add deployment baseline with `Dockerfile` and `docker-compose.yml` using gunicorn.
- [x] Add optional Basic Auth via `flask-httpauth` and env-driven credentials.
- [x] Add reverse proxy examples in `docs/reverse-proxy.md`.
- [x] Add first Phase 3 analyzer module: `app/analyzers/response_patterns.py`.
- [x] Add API endpoint `/api/chat/<id>/response-patterns`.
- [x] Add Phase 3 media/link analyzer module: `app/analyzers/media_links.py`.
- [x] Add API endpoint `/api/chat/<id>/media-links`.
- [x] Add LLM structure notes: `docs/llm-integration.md` plus config placeholders.
- [x] Add Phase 3 topics analyzer module: `app/analyzers/topics.py` (TF-IDF + NMF).
- [x] Add API endpoint `/api/chat/<id>/topics`.
- [x] Add Phase 3 relationships analyzer module: `app/analyzers/relationships.py`.
- [x] Add API endpoint `/api/chat/<id>/relationships`.
- [x] Add Plotly-oriented payload shaping in `app/charts_payloads.py`.
- [x] Add API endpoint `/api/chat/<id>/dashboard-data` for UI consumption.
- [x] Wire `/results/<analysis_id>` to interactive tabbed dashboard + filters using Plotly payloads.
- [x] Add chart-level loading/error states and session cache fallback for dashboard API payload.
- [x] Add persisted dashboard filter preferences (person + date range) via localStorage.
- [x] Add date-level filtering across dashboard API-driven traces.
- [x] Add dashboard chart legends/tooltips polish with mobile-friendly legend layout.
- [x] Add deprecation warnings to legacy wrapper scripts (`wa-stats.py`, `wa-stats-flask.py`, `wa-graphs.py`, `wa-flask.py`).
- [x] Update Docker deployment config to use `.env`-driven settings and health checks.
- [x] Add mobile-over-Tailscale deployment guidance to README.
- [x] Add recent-analysis session loading on upload page via new `GET /api/chats` endpoint, including "static files missing" warnings.
- [x] Add bundled demo chat flow (`data/sample-chat.txt` + `/demo`) with upload-page shortcut for quick onboarding.
- [x] Add per-chart PNG downloads for interactive Plotly charts plus explicit PNG download links in the Static Graphs tab.
- [x] Improve mobile dashboard tab UX with horizontal tab scrolling and 44px touch targets for tabs/filter apply button.
- [x] Add Activity day-of-week x hour heatmap payload and interactive chart in the dashboard Activity tab.
- [x] Add Activity response-time distribution chart (box plot, capped at 24h) using per-response delay tuples.
- [x] Improve upload error handling with friendly parser-failure messages, AJAX redirect/error detection, and retry UI.
