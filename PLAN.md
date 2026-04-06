# Kaajd Improvement Plan

## Context

Kaajd is a WhatsApp chat analyzer built for fun — parse a chat export, get stats and graphs. Currently ~350 lines of Python across 4 scripts with basic Flask web UI. The goal: make it significantly more capable (new analyses, interactive dashboard, multilingual) and hostable (Docker, auth), while preparing the architecture for future LLM integration.

## Progress snapshot (working state)

- **Phase 1:** largely completed; compatibility wrappers still present as deprecated shims.
- **Phase 2:** completed for practical use (multi-format parser, enrichment, SQLite, cache reuse).
- **Phase 3:** major modules implemented (`response_patterns`, `media_links`, `topics`, `relationships`).
- **Phase 4:** interactive Plotly dashboard and API payload flow implemented; polish ongoing.
- **Phase 5:** Docker/gunicorn/auth baseline implemented; deployment hardening docs ongoing.
- **Phase 6:** structure in place (context/query APIs, config placeholders, integration docs); runtime LLM features intentionally not implemented.

---

## Phase 1: Restructure and Consolidate

Merge duplicates, create proper project structure, fix deprecated APIs.

**New structure:**
```
kaajd/
  app/
    __init__.py          # Flask app factory
    parser.py            # Merged parsing (wa-stats.py + wa-stats-flask.py)
    analyzer.py          # Stats computation
    graphs.py            # Graph generation (wrapped in functions)
    routes.py            # Flask routes
    templates/
      base.html
      upload.html
      dashboard.html
    static/
      css/
      uploads/
  cli.py                 # CLI entry point
  config.py              # Configuration
  requirements.txt
  Dockerfile
  docker-compose.yml
```

**Key changes:**
- Merge `wa-stats.py` + `wa-stats-flask.py` → `app/parser.py` with `parse_chat(file_path, output_dir=None)`
- Fix deprecated `df.append()` → `pd.concat()`
- Wrap `wa-graphs.py` procedural code into functions
- Stop using `subprocess.run()` — import Python functions directly
- Create `requirements.txt`

**Delete after migration:** `wa-stats.py`, `wa-stats-flask.py`, `wa-graphs.py`, `wa-flask.py`

---

## Phase 2: Parser Improvements + Data Layer

Robust parsing, language detection, SQLite storage (LLM-ready).

**Multi-format parser:** Support WhatsApp export variations:
- `DD-MM-YYYY HH:MM` (Dutch), `MM/DD/YY, HH:MM` (US), `DD/MM/YYYY, HH:MM` (UK), bracketed Android format
- Auto-detect by testing patterns against first 5 lines

**Message enrichment:**
- Flag system messages (no colon in sender portion)
- Flag media messages (`<Media weggelaten>` / `<Media omitted>`)
- Flag messages with URLs (`has_link`)
- Auto-detect language via `langdetect` on sample of messages

**SQLite layer** (`app/database.py`):
- Tables: `chats`, `messages`, `stats`
- Avoids re-parsing on repeat views
- Queryable for future LLM integration
- Enables cross-chat analysis

**New dependency:** `langdetect`

---

## Phase 3: New Analyses

Four new analysis modules in `app/analyzers/`.

**3A — Response Patterns** (`response_patterns.py`):
- Average response time between different senders
- "Who replies to whom" transition matrix
- Extended conversation starter analysis (who responds first, avg conversation length)

**3B — Topic Detection** (`topics.py`):
- TF-IDF per time window (monthly buckets) for trending terms
- Lightweight topic clustering via NMF or LDA (3-5 topics)
- Language-aware stopwords from Phase 2

**3C — Media & Link Stats** (`media_links.py`):
- Media/link counts per person (using Phase 2 flags)
- Breakdown by time period
- Top shared domains
- Media-to-text ratio per person

**3D — Relationship Dynamics** (`relationships.py`):
- Affinity scores from reply matrix (group chats)
- Activity correlation (Pearson on daily message counts per pair)
- Balance metrics for 2-person chats (initiative, response time asymmetry)

**New dependency:** `scikit-learn` (TF-IDF, topic modeling)

---

## Phase 4: UI Overhaul

Interactive Plotly dashboard replacing static PNGs.

**Charts (Plotly.js via CDN, no Dash):**
- Convert all 7 existing graphs to interactive Plotly
- Word cloud stays as matplotlib (base64-embedded) — Plotly can't do word clouds
- Emoji chart can now show actual emoji characters (browser rendering)
- Add new charts: response time heatmap, reply network, topic trends, media patterns

**Dashboard layout:**
- Bootstrap 5 with dark/light mode toggle (CSS variables)
- Tabbed layout: Overview | Activity | Topics | Relationships | Media
- Person filter dropdown + date range picker (client-side JS filtering)
- Stat summary cards in Overview tab
- Drag-and-drop file upload with progress spinner

**Files:** `app/charts.py` (replaces `graphs.py`), new templates

---

## Phase 5: Deployment

Docker + auth for hosting.

- **Dockerfile:** Python 3.11-slim, gunicorn, NLTK data download
- **docker-compose.yml:** Volume for SQLite + uploads, env vars for auth
- **Basic auth:** `flask-httpauth` with credentials from environment variables
- **Gunicorn** as WSGI server
- **Reverse proxy docs:** Sample Caddy/nginx config for HTTPS

**New dependencies:** `gunicorn`, `flask-httpauth`

---

## Phase 6: LLM-Ready Architecture (Structure Only)

Prepare integration points without building LLM features.

- JSON API endpoint `/api/chat/<id>/context` returning structured analysis summary
- Query helper `query_messages(chat_id, filters...)` for message retrieval
- Config placeholders for LLM endpoint (Open WebUI compatible)
- Documentation in `docs/llm-integration.md` describing how to add:
  - **Snarky commentary:** Feed chat stats + context to LLM, display generated roasts/observations per chart
  - **Chat Q&A:** User asks questions about their chat history, relevant messages retrieved via SQL and sent to LLM
  - **Time-windowed summaries:** Monthly/yearly chat summaries generated by sending message batches to LLM

---

## Recommended Phase Order

```
Phase 1 (Restructure) → Phase 2 (Parser + SQLite) → Phase 5 (Deploy early)
                                                   → Phase 3 (Analyses) → Phase 4 (UI)
                                                   → Phase 6 (LLM-ready)
```

Deploy early (Phase 5 after 2) so you can share WIP with friends while building the fun stuff. Analyses before UI so the dashboard has data to show.

---

## Key Libraries

| Library | Purpose | Phase |
|---------|---------|-------|
| `langdetect` | Auto-detect chat language | 2 |
| `scikit-learn` | TF-IDF, topic modeling | 3 |
| `plotly` | Interactive charts (JS via CDN) | 4 |
| `gunicorn` | Production WSGI server | 5 |
| `flask-httpauth` | Basic authentication | 5 |

Existing libraries retained: `flask`, `pandas`, `matplotlib` (CLI + word cloud), `seaborn`, `statsmodels`, `wordcloud`, `emoji`, `textblob`, `nltk`, `beautifulsoup4` (can drop after Phase 1).

---

## Verification per Phase

- **Phase 1:** `python cli.py data/chat.txt` produces same output. Flask upload→results flow works.
- **Phase 2:** Dutch and English exports both parse. SQLite populated. Language detected correctly.
- **Phase 3:** New analysis results returned (even with basic UI).
- **Phase 4:** Interactive charts render, filters work, dark mode toggles.
- **Phase 5:** `docker compose up` starts app, auth prompts on access.
- **Phase 6:** `/api/chat/1/context` returns valid JSON summary.
