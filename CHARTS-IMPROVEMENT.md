# Charts Improvement Plan

Generated: 2026-04-06. Based on a fresh visual critique of all 17 charts in `/sample/` and a comparison with the earlier `CHART-REVIEW.md` evaluation.

---

## Fresh Critique vs CHART-REVIEW.md — What Changed

The earlier `CHART-REVIEW.md` captured the main structural problems accurately. After viewing every chart directly, these are the **new or expanded findings** that weren't fully covered:

### New findings not in CHART-REVIEW.md

1. **`kaajd-correlation-heatmap.png` was not reviewed at all.** It has the same Y-axis truncation problem as the other two heatmaps (label text is cut to "s Maes", "tublieft", "Waajen", etc.) and also lacks axis titles. The "Meta AI" row and column produce an interesting artefact: near-zero correlation with all humans (the bot replies to every message regardless of day, so its daily counts don't co-vary with any participant's). This should be called out explicitly.

2. **`message_length_distribution.png` was not reviewed at all.** It is a histogram capped at the 95th percentile (~175 chars) with 30 bins and a bimodal shape. The chart is functional but has the same dated Matplotlib aesthetic, contains no per-person breakdown, and the bin-edge spacing creates an odd gap around 10–15 characters that may be misleading.

3. **The Meta AI participant distorts multiple charts.** "Meta AI" (WhatsApp's built-in AI assistant) appears as a first-class participant throughout:
   - In `kaajd-response-time-distribution.png`, its near-instant response distribution is visually isolated and skews the scale comparison.
   - In the response/affinity/correlation heatmaps, its row and column produce near-zero or structurally different values that confuse the human-to-human signal.
   - In `kaajd-conversation-starters.png`, it appears with 0 starters — technically correct but visually cluttering.
   - **None of this is mentioned in CHART-REVIEW.md.** Meta AI should be filterable or excluded from response/relationship analyses by default, with an option to re-include it.

4. **Y-axis label truncation on all three heatmaps** — CHART-REVIEW.md only noted missing axis *titles*. In practice, the long participant name "Simon Vier Jansen Kassa Vier Alstublieft" also causes the left-margin to overflow and clips *all* y-axis labels. The visible labels become unreadable partial strings. This is a layout bug, not just a labeling gap.

5. **`kaajd-conversation-starters.png` is sorted alphabetically, not by value.** The Matplotlib `conversation_starters.png` is correctly sorted descending by count (Nardy first). The Plotly replacement silently dropped this: it now shows `Florian → Jasper → Jeroen → Meta AI → Nardy → Simon → Tjores` in alphabetical order. This is a usability regression — a bar chart ranked by count communicates a clear winner; alphabetical order obscures it.

6. **TextBlob sentiment is unreliable for Dutch.** `sentiment.png` is generated using `TextBlob`, which is trained on English text. This Dutch-language chat will produce near-random polarity scores for most messages. The flatness of the trend line at ~0.05 is partly a consequence of noisy/wrong scores, not just statistical averaging. Any sentiment chart should either use a Dutch-capable model (`transformers`, `pattern`, or `flair` with a Dutch checkpoint) or be clearly labelled as "English-word only" with a caveat.

7. **`kaajd-day-hour-activity.png` day ordering.** The chart puts Sunday at top (row 0) and Monday at bottom (row 6). For a European chat in Dutch, Monday-at-top is the conventional week layout. This is a minor convention mismatch but easy to fix by reversing the `weekday_labels` list and the matrix row order.

### Confirmed and expanded findings from CHART-REVIEW.md

The earlier review's findings are all confirmed. Key additions:

- **`kaajd-topic-labels.png`**: The bar heights are literally the topic index (1, 2, 3, 4, 5) — there is no meaningful metric mapped to height at all. The ascending staircase pattern is a dead giveaway. The NMF topics themselves are nearly useless because Dutch stop words are not applied to the topic modeling pipeline (`app/analyzers/topics.py`): terms like "niet", "maar", "dan", "heb" dominate every topic.

- **`kaajd-media-monthly-trends.png`**: 14 overlapping lines confirmed. Most lines cannot be distinguished in the final render; the legend (14 entries) occupies roughly 25% of the chart height.

- **`kaajd-response-time-distribution.png`**: The Y-axis runs to 1440 minutes (24 hours) but over 90% of the data points are below 200 minutes. The violin shapes are technically computed but visually flattened to a thin line. The redundant legend at the bottom exactly duplicates the X-axis labels.

- **`kaajd-top-shared-domains.png`**: `youtube.com` (575) and `youtu.be` (354) are separate entries. Combined YouTube would total 929 — nearly 3× the #3 domain (`nos.nl` at 270). This misrepresents YouTube's dominance. `f7id5.app.goo.gl` and `m.limburg.nl` near the end are near-zero-count noise that could be filtered to a top-15 cutoff.

---

## Priority Improvement Plan

Organized by effort/impact. Each item includes the source file(s) to change.

---

### P0 — Critical Bugs (data correctness / broken rendering)

#### B1 · Fix emoji name concatenation bug in `top_emojis.png`
**File:** `app/graphs.py:_plot_top_emojis`

The `emoji.demojize()` call produces names like `:rolling_on_the_floor_laughing:`. The regex replacements strip the colons and replace underscores with spaces, which is correct in isolation. However, the pandas `Series.value_counts()` is called on the **raw emoji characters** (which may match multiple Unicode codepoints as a single entry depending on the regex `+` quantifier). When the emoji regex uses `+`, it can group consecutive emoji characters into a single match, producing labels like `"rolling on the floor laughingrolling on the floor laughing"`. Fix: extract **individual** emoji characters (iterate, don't batch-match with `+`), then demojize each one separately.

```python
# Fix: replace the regex-based extractor with emoji.emoji_list()
def _extract_emojis(value: str) -> list[str]:
    return [item["emoji"] for item in emoji.emoji_list(value)]
```

#### B2 · Fix alphabetical sort in `kaajd-conversation-starters.png`
**File:** `app/charts_payloads.py:_response_patterns_payload`

The `conversation_starters_bar` payload preserves the order returned by `response_patterns.py`. Confirm that the analyzer already returns entries sorted by `conversations_started DESC`; if not, add an explicit sort in the payload builder:

```python
starters_sorted = sorted(starters, key=lambda x: x.get("conversations_started", 0), reverse=True)
```

Then use `starters_sorted` when building `x` and `y` lists.

#### B3 · Fix Y-axis label clipping on all three heatmaps
**File:** `app/templates/dashboard.html` (Plotly layout for response, affinity, correlation heatmaps)

The left margin is too narrow to accommodate long names. Add `margin: { l: 220 }` (or compute dynamically as `max_name_length * 7` px) in each heatmap's Plotly layout. Also truncate long names server-side in the payload to a max of ~22 characters with an ellipsis:

```python
def _truncate(name: str, max_len: int = 22) -> str:
    return name if len(name) <= max_len else name[:max_len - 1] + "…"
```

Apply `_truncate` to all heatmap `x` and `y` label lists in `charts_payloads.py`.

#### B4 · Fix NMF topic stop words — topics are all filler words
**File:** `app/analyzers/topics.py`

The topic modeling pipeline likely does not apply an aggressive Dutch stop word list before running TF-IDF. Add the same `custom_stops` set used in `graphs.py:_plot_wordcloud` (plus NLTK Dutch stop words) to the TF-IDF vectorizer's `stop_words` parameter. TF-IDF's built-in `stop_words='english'` does nothing for Dutch. Example:

```python
from nltk.corpus import stopwords
dutch_stops = list(stopwords.words("dutch")) + list(CUSTOM_STOPS)
vectorizer = TfidfVectorizer(stop_words=dutch_stops, ...)
```

---

### P1 — Replace Legacy Matplotlib Charts

All six Matplotlib-generated charts should be migrated to Plotly and served through the dashboard API. The static PNG fallback tab can still show them, but the primary interactive dashboard should use Plotly equivalents.

#### M1 · Replace `messages_over_time.png` → monthly bar chart
**Replace:** scatter plot of daily counts  
**With:** vertical bar chart aggregated by **month** (or week for short chats), with a smooth trend overlay  
**Add to payload:** `app/charts_payloads.py:_activity_payload` — group `raw_data_df` by `YYYY-MM` month bucket, count messages, return as a `monthly_volume` trace  
**Chart type:** `go.Bar` with a `go.Scatter` LOWESS overlay  
**Why:** Daily scatter creates a confetti cloud that hides the actual trend. Monthly bars show volume at a readable granularity.

#### M2 · Replace `sentiment.png` → monthly per-person sentiment (or drop)
**Replace:** per-message polarity vs. message index  
**With:** monthly rolling average polarity per person, with date on X-axis  
**Critical prerequisite:** Switch from TextBlob to a Dutch-capable sentiment model, or clearly scope the analysis to English-only words in the message. If a Dutch model is not feasible, replace this chart with a "sentiment by participant" summary bar (average polarity per person as a ranked bar chart), which is less misleading than a time series of random-looking values.  
**Add to payload:** `app/charts_payloads.py:_activity_payload` with a `sentiment_monthly` key  
**Chart type:** `go.Scatter` with one trace per person, `mode='lines'`

#### M3 · Replace `most_active_times.png` → remove (superseded by heatmap)
The `kaajd-day-hour-activity.png` heatmap already communicates everything `most_active_times.png` does, more clearly. Remove `most_active_times.png` from the static tab entirely and from the `generate_graphs()` call in `graphs.py`. The interactive heatmap is already in the dashboard.

#### M4 · Replace `top_emojis.png` → Plotly horizontal bar with emoji characters
**Replace:** vertical Matplotlib bar with text labels  
**With:** Plotly `go.Bar(orientation='h')` using actual emoji Unicode characters as Y-axis tick labels  
**Why:** Browsers render emoji natively; no need for CLDR text names. Horizontal orientation fits long emoji sequences better.  
**Add to payload:** `app/charts_payloads.py` — add `emoji_counts` key in `_activity_payload` or a new top-level section. Compute using `emoji.emoji_list()` (fixes B1 simultaneously).

#### M5 · Upgrade `message_length_distribution.png` → Plotly with per-person breakdown
**Replace:** single global histogram  
**With:** Plotly `go.Histogram` overlaid per person (or a box plot per person showing median/IQR of message length)  
**Add to payload:** `app/charts_payloads.py:_activity_payload` — compute per-person message lengths and return as distribution traces  
**Chart type:** `go.Box` (one box per person, sorted by median) is more compact and informative than overlapping histograms

#### M6 · Upgrade `conversation_starters.png` → use the Plotly version but fix it (see B2)
The Plotly version already exists; the Matplotlib version can be removed from `graphs.py` once the sort order is fixed (B2).

---

### P2 — Fix Existing Plotly Charts

#### F1 · `kaajd-topic-labels.png` — replace entirely
**Current problem:** bar heights = topic index (meaningless); topic terms are filler words  
**Replacement:** A styled table or card grid showing each topic as a "chip cluster" of its top 5 terms. No bars needed — the terms are the data. In Plotly, this can be rendered as an `go.Table` or as an annotated scatter/treemap. Alternatively, a **heatmap of term weights** (topics on X, top terms on Y, cell color = TF-IDF weight) is more honest about what NMF actually computes.  
**Must fix B4 first** (stop words) or the replacement chart will still show filler words.

#### F2 · `kaajd-response-time-distribution.png` — log Y-axis or cap at 4 hours
**Current problem:** Y-axis 0–1440 min squishes the core data  
**Fix options (choose one or combine):**
  - Apply `yaxis_type="log"` in the Plotly layout — log scale makes both the short responses (2–10 min) and the long waits (hours) visible simultaneously
  - Hard-cap the display at **4 hours (240 min)** instead of 24 hours; add an annotation "X% of responses capped" to acknowledge outliers
  - The 24-hour cap already exists in `charts_payloads.py`; just tighten it to 240 min or use log
**Also:** remove the redundant legend (it duplicates X-axis labels); add Y-axis title "Response time (minutes)"

#### F3 · `kaajd-response-heatmap.png` — add axis titles, fix white NaN cells
**Add:** `xaxis_title="Sender"`, `yaxis_title="Responder"` (or clarify the exact directionality from `response_patterns.py`)  
**Fix:** Replace `None` Z-values with a distinct sentinel (e.g., use `colorscale` with a special color for NaN, or pre-fill with `-1` and use `zmin=0`). Plotly supports `colorscale` with a NaN-color via `nacolor`. Example: `go.Heatmap(colorscale=..., nacolor='lightgray')`  
**Also:** Apply B3 (Y-axis margin) and name truncation

#### F4 · `kaajd-affinity-heatmap.png` — clarify color scale and add axis titles
**Current problem:** Gray ≈ 0 affinity looks like "missing data"  
**Fix:** Use a sequential colorscale that transitions from white (zero affinity) to the brand color (high affinity) rather than gray-to-blue. White clearly reads as "no relationship." Add `xaxis_title="Replied to →"`, `yaxis_title="Replier ↓"`.  
**Also:** Apply B3 name truncation

#### F5 · `kaajd-correlation-heatmap.png` — add axis titles, handle Meta AI
**Add:** `xaxis_title="Participant"`, `yaxis_title="Participant"` and a subtitle/annotation explaining the metric ("Pearson correlation of daily message counts")  
**Consider:** Flag or visually separate the Meta AI row/column (e.g., dashed border cells) since its correlation structure is fundamentally different from human participants

#### F6 · `kaajd-media-links-per-person.png` — add Y-axis title
**Add:** `yaxis_title="Number of messages"`. One-line fix in `dashboard.html`.

#### F7 · `kaajd-media-monthly-trends.png` — replace with faceted small multiples or aggregate total
**Option A (recommended):** Replace with a **stacked area chart of total group media + links** per month. Two areas (media vs. links) over time gives the overall trend without person-level noise.  
**Option B:** Small multiples (facets) — one mini-line-chart per person, each showing their media and links separately. Plotly supports this via subplots.  
**If keeping per-person:** restrict to top 3–4 contributors and group the rest as "Others"

#### F8 · `kaajd-top-shared-domains.png` — normalize youtu.be → youtube.com, add axis title, cap at 15
**Data fix (in `app/analyzers/media_links.py`):** Add a domain normalization step before counting:
```python
DOMAIN_ALIASES = {
    "youtu.be": "youtube.com",
    "m.youtube.com": "youtube.com",
    "mobile.twitter.com": "twitter.com",
    "m.facebook.com": "facebook.com",
    # extend as needed
}
domain = DOMAIN_ALIASES.get(domain, domain)
```
**Chart fix:** `yaxis_title="Number of links"`, limit to top 15 domains in the payload builder

#### F9 · `wordcloud.png` — expand Dutch stop words
**File:** `app/graphs.py:_plot_wordcloud`  
Add the following high-frequency conversational Dutch words to `custom_stops`:
`"echt", "net", "gewoon", "misschien", "jullie", "ook", "nog", "dit", "die", "dat", "een", "wat", "hoe", "als", "dan", "maar", "meer", "had", "heeft", "heb", "hem", "zijn", "deze", "kunnen", "moeten", "weten", "zeker"`  
The current stop word list is a good start but these filler words still dominate the cloud.

#### F10 · `kaajd-day-hour-activity.png` — reverse day ordering to Mon–Sun top to bottom
**File:** `app/charts_payloads.py:_activity_payload`  
Change `weekday_labels = ["Mon", "Tue", ..., "Sun"]` to `["Sun", "Sat", ..., "Mon"]` (reversed) so that Monday appears at the top of the Y-axis. This matches the European convention of Monday as the first weekday and makes the heatmap read more naturally (Mon → Sun top to bottom).

---

### P3 — Meta AI Handling (cross-cutting)

**File:** `app/charts_payloads.py` (all payload builders), `app/analyzers/response_patterns.py`, `app/analyzers/relationships.py`

Add a configurable list of bot/system participant names to exclude from relationship and response analyses (but keep in message-count totals):

```python
BOT_PARTICIPANTS = {"Meta AI", "meta ai"}  # case-insensitive match
```

In `_response_patterns_payload` and `_relationships_payload`, filter out entries where `from` or `to` is in `BOT_PARTICIPANTS` before building heatmap matrices. Add a note in the chart subtitle ("Excluding: Meta AI") so the exclusion is transparent.

---

### P4 — New Visualizations

These are net-new charts that address gaps in the current set.

#### N1 · Monthly message volume bar chart (replaces scatter)
See M1 above. The highest-value new chart — makes the time-volume trend actually readable.

#### N2 · Per-person message length box plot
See M5 above. Reveals whether some participants write long paragraphs vs. short reactions.

#### N3 · Monthly participation bump chart (rank over time)
A "race chart" showing each participant's rank by monthly message count over the years. Each person is a line; Y-axis is rank (1 = most active that month). Shows the shift of who drives the chat. Already documented in `IMPROVEMENTS.md` (item 3H). Data is available from the messages table.

#### N4 · Emoji chart per person
Show the top 3 emojis per participant as a grouped bar or small-multiples grid. Adds personality context to the overall emoji chart.

---

## Summary Table

| # | Chart | Problem | Action | Priority |
|---|-------|---------|--------|----------|
| B1 | `top_emojis.png` | Emoji name concatenation bug | Fix `_extract_emojis` to use `emoji.emoji_list()` | P0 |
| B2 | `kaajd-conversation-starters.png` | Alphabetical sort (regression) | Sort payload by count DESC | P0 |
| B3 | All 3 heatmaps | Y-axis labels truncated | Add left margin + name truncation in payload | P0 |
| B4 | `kaajd-topic-labels.png` | Topic terms are all filler words | Apply Dutch stop words to TF-IDF in `topics.py` | P0 |
| M1 | `messages_over_time.png` | Daily scatter → unreadable noise | Replace with monthly bar chart in Plotly | P1 |
| M2 | `sentiment.png` | Message-index X-axis, TextBlob on Dutch | Monthly average per person, date X-axis; flag Dutch reliability | P1 |
| M3 | `most_active_times.png` | Superseded by heatmap | Remove from generate_graphs() | P1 |
| M4 | `top_emojis.png` | Matplotlib, text labels | Plotly horizontal bar with real emoji chars | P1 |
| M5 | `message_length_distribution.png` | Single global histogram, dated style | Plotly box plot per person | P1 |
| M6 | `conversation_starters.png` | Deprecated Matplotlib version | Remove after B2 fix validates Plotly version | P1 |
| F1 | `kaajd-topic-labels.png` | Bar heights = topic index (meaningless) | Replace with term-weight heatmap or card grid | P2 |
| F2 | `kaajd-response-time-distribution.png` | Y-axis 0–1440 min squishes data | Log scale or 4h cap; remove redundant legend | P2 |
| F3 | `kaajd-response-heatmap.png` | White NaN cells, no axis titles, truncated labels | nacolor='lightgray', add titles, apply B3 | P2 |
| F4 | `kaajd-affinity-heatmap.png` | Gray≈0 looks like missing data, no axis titles | White→color scale, add titles, apply B3 | P2 |
| F5 | `kaajd-correlation-heatmap.png` | No axis titles, Meta AI structural anomaly | Add titles, annotate Meta AI row/col | P2 |
| F6 | `kaajd-media-links-per-person.png` | Missing Y-axis title | Add `yaxis_title` | P2 |
| F7 | `kaajd-media-monthly-trends.png` | 14-line spaghetti | Replace with stacked area (total) or small multiples | P2 |
| F8 | `kaajd-top-shared-domains.png` | youtu.be ≠ youtube.com, no Y title, 20 domains | Domain alias normalization, add title, cap at 15 | P2 |
| F9 | `wordcloud.png` | Dutch filler words dominate | Expand custom_stops with common conversational Dutch | P2 |
| F10 | `kaajd-day-hour-activity.png` | Sun at top (non-European convention) | Reverse row order to Mon–Sun | P2 |
| P3 | All relationship/response charts | Meta AI distorts human-to-human analysis | Add BOT_PARTICIPANTS exclusion filter | P2 |
| N1 | *(new)* | Monthly volume trend missing | Add monthly bar chart payload | P3 |
| N2 | *(new)* | No per-person message length view | Add box plot per person payload | P3 |
| N3 | *(new)* | No participation rank-over-time view | Add bump chart payload | P3 |
| N4 | *(new)* | No per-person emoji personality data | Add per-person top-emoji chart | P3 |

---

## Implementation Order

1. **Start with P0 bugs** — they make charts actively wrong or broken. B1 and B2 are one-liners; B3 and B4 are ~20 lines each.
2. **Meta AI exclusion (P3 cross-cutting)** — affects 5+ charts; do before polishing heatmaps.
3. **Replace Matplotlib charts (P1)** — reduces technical debt and visual inconsistency. M3 is just a deletion.
4. **Fix existing Plotly charts (P2)** — incremental polish; F6 is a one-liner.
5. **New visualizations (P4)** — additive; no existing charts broken if deferred.
