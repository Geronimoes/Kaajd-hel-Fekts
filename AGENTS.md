# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## What this is

**Kaajd** is a WhatsApp chat export analyzer. It parses WhatsApp `.txt` export files and produces statistics and graphs. Two usage modes: CLI scripts and a Flask web app.

## Running the scripts

**CLI workflow (run in order):**
```bash
python3 wa-stats.py /path/to/chat.txt   # generates CSV, HTML, JSON stats
python3 wa-graphs.py /path/to/chat.txt  # generates PNG graphs (requires CSV from wa-stats.py)
```
Default input path if no argument given: `./data/chat.txt`

**Web app:**
```bash
python3 wa-flask.py   # starts server on port 5000
```

## Architecture

The project has two parallel code paths that do the same parsing:

- **CLI path**: `wa-stats.py` → `wa-graphs.py` (sequential, standalone)
- **Web path**: `wa-flask.py` calls `wa-stats-flask.py` + `wa-graphs.py` via `subprocess.run()`

`wa-stats-flask.py` is a near-duplicate of `wa-stats.py` — the difference is how it resolves the output directory relative to the uploaded file. The web app uploads files to `./static/`, stores output under `./static/<timestamp-filename>/<basename>/output/`.

**Output files** (always written to `<input_dir>/<basename>/output/`):
- `raw-data.csv` — parsed messages (Date, Time, Person, Message columns)
- `summary.html` / `summary.json` — per-person stats table
- `messages_over_time.png`, `most_active_times.png`, `conversation_starters.png`, `message_length_distribution.png`, `wordcloud.png`, `top_emojis.png`, `sentiment.png`

**WhatsApp date format** expected by the regex: `DD-MM-YYYY HH:MM - Person: message`

## Dependencies

Key packages: `flask`, `pandas`, `matplotlib`, `seaborn`, `statsmodels`, `wordcloud`, `emoji`, `textblob`, `nltk`, `beautifulsoup4`

NLTK Dutch stopwords must be downloaded once before first use:
```python
import nltk; nltk.download('stopwords')
```
(Already downloaded on the server; commented out in `wa-graphs.py:117`)

## Known issues / tech debt

- `wa-stats.py` and `wa-stats-flask.py` are nearly identical — not yet merged
- `chat_stats_df.append()` in both stats scripts uses the deprecated pandas API (use `pd.concat` instead)
- Sentiment analysis via TextBlob is English-only; chat is in Dutch, so results are approximate
