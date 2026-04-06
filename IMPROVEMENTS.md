# Kaajd — Improvement Advisory

Generated: 2026-04-06. Covers four areas: session loading, mobile UX + exports, new analyses, and general improvements.

---

## 1. Loading Earlier Sessions and Sample Data

### 1A — Previous-Session Loader

The server already stores every analysis in SQLite (`chats` table: `id`, `source_name`, `created_at`, `message_count`, `output_dir`). The only missing piece is a UI to list and re-open them.

**What to build:**

- Add a "Recent analyses" section directly beneath the upload form on `upload.html`. Query the `chats` table ordered by `created_at DESC` (limit 10). For each row show: filename, upload date, message count, detected language.
- Each row links to `/results/<analysis_id>?chat_id=<id>`. The `analysis_id` can be derived from `output_dir` (it is the last path component, e.g. `1712345678-chatfile`).
- Add a new route `GET /api/chats` that returns the same list as JSON (useful for future JS rendering or a dedicated `/history` page).
- Optionally add a delete button per row (calls `DELETE /api/chat/<id>`) to manage disk space.

**Key consideration:** if `output_dir` no longer exists on disk (e.g. the uploads folder was cleaned), the static graphs and CSV downloads will 404. Show a warning badge ("static files missing") in that case.

**Minimal implementation path:**
1. `GET /api/chats` → query `chats` table → return JSON list.
2. Add a small `<ul>` block in `upload.html` populated by a `fetch('/api/chats')` call on page load.
3. Each item: link to `/results/<analysis_id>?chat_id=<id>`.
4. No new template required; just JS + one new route.

---

### 1B — Sample / Demo Data

Useful for: first-time visitors, testing deployments, screenshots/demos.

**What to build:**

- Bundle a small synthetic chat file at `data/sample-chat.txt` (generate ~500 messages across 3–4 fake people, covering a range of dates, emojis, links, media references).
- Add a "Try with demo data" button on `upload.html`. Clicking it POSTs to a new `GET /demo` route that runs `analyze_chat()` on the bundled file and redirects to the results page.
- The sample chat should use a plausible format (e.g. Dutch `DD-MM-YYYY HH:MM`) to exercise the full parser pipeline.
- Since the hash is consistent, re-clicking "Demo" will always reuse the SQLite cache and be instant after the first run.

**Both 1A and 1B can be implemented independently.** 1A provides real value for repeat users; 1B is primarily useful for public demos and onboarding.

---

## 2. Mobile UX and Export / Download

### 2A — Mobile UX Gaps

The current state is decent (responsive Bootstrap grid, Plotly `responsive: true`, mobile legend repositioning) but several rough edges remain:

**Tab overflow on small screens**

Six Bootstrap tabs in a single row overflow on phones (screen ≤ 375px). Fix: add `overflow-x: auto; white-space: nowrap;` to the `.nav-tabs` container, or switch to a `<select>` dropdown on mobile (swap via CSS media query).

**Dense heatmaps on mobile**

The response-time heatmap, affinity heatmap, and topics heatmap become unreadable at 280px height when participant counts are moderate (≥ 4 people). Increase mobile chart height for heatmaps specifically (e.g. `max(280px, 60px * n_rows)`). Pass `height` dynamically from the payload or compute it client-side from the data array length.

**Axis label clipping**

Plotly axis labels truncate on narrow viewports. For mobile, reduce the number of tick labels shown (`nticks: isMobile() ? 5 : null`) and increase the left margin to prevent y-axis label cropping.

**Filter bar on mobile**

The person dropdown + two date inputs + Apply button stack decently but the date inputs are narrow. Replace or supplement with `<input type="date">` native inputs (already mobile-friendly) and ensure the Apply button is full-width on mobile.

**Touch target sizes**

Tab buttons and the filter Apply button should be at least 44×44 px on mobile (WCAG 2.5.5). Add `min-height: 44px; padding: 10px 16px;` to tab nav-links via the mobile media query.

**Swipe navigation between tabs**

Optional enhancement: add `Hammer.js` (or a small vanilla touch-event handler) to swipe left/right between tabs on mobile. Low cost, high UX polish.

**PWA / Add to Home Screen**

Add `manifest.json` and a minimal service worker (offline cache of static assets only — no caching of analysis data). Allows mobile users to install Kaajd as a home screen app. Low-effort, meaningful for self-hosted use over Tailscale.

---

### 2B — Per-Chart Download Buttons

Plotly already ships a `downloadImage` API. For every chart, show a small download button (SVG icon, 28px) overlaid on the top-right corner. On click:

```javascript
Plotly.downloadImage(chartDiv, {
    format: 'png',
    width: 1200,
    height: 600,
    filename: 'kaajd-response-heatmap'
});
```

Add this pattern once in a shared `addDownloadButton(divId, filename)` helper and call it after each `Plotly.newPlot()`. Static graph PNGs in the Static tab are already downloadable via right-click; add explicit download links (`<a download href="...">`) next to each image for consistency.

---

### 2C — Full Report Download (PDF)

A one-click "Download full report" button that produces a self-contained PDF containing:

- Chat metadata summary (name, date range, participants, message count)
- All stat cards and the per-person table
- All interactive chart screenshots (rendered as PNGs server-side or embedded via Plotly's static image export)
- All static graph PNGs

**Server-side approach (recommended):**

Use `weasyprint` (pure Python, no headless browser needed) to render a print-optimized HTML template to PDF.

```
GET /report/<chat_id>.pdf
```

Route: fetch all analysis data from DB, render a `report.html` template (no JS, no Bootstrap, just clean print CSS and base64-embedded images), pass to `weasyprint.HTML(...).write_pdf()`, return as `application/pdf`.

This avoids a Chromium/Puppeteer dependency. `weasyprint` handles CSS paged media, page breaks, and embedded images well.

**New dependency:** `weasyprint` (Python, ~5 MB).

---

### 2D — ZIP Export

A "Download all data" button that produces a ZIP containing:

- `raw-data.csv`
- `summary.json`
- All static `.png` graph files
- (optionally) a `report.html` self-contained HTML file with embedded charts

Route `GET /export/<analysis_id>.zip` built with Python's `zipfile` module. No new dependencies.

---

### 2E — Web Share API

On mobile browsers that support it (`navigator.share`), show a "Share" button on the dashboard that calls `navigator.share({ title: 'Kaajd analysis', url: window.location.href })`. Fall back to a "Copy link" clipboard button on unsupported browsers. One-liner JS addition.

---

## 3. Additional Analyses and Visualizations

### 3A — Day-of-Week × Hour Activity Heatmap (high value, low effort)

The single most requested WhatsApp stat visualization. A 7×24 heatmap (rows = days of week Mon–Sun, columns = hours 0–23) colored by message count. Shows "when is this chat most active?" at a glance.

- Data: already available from the `messages` table (parse `date` + `time` columns).
- Add to the **Activity** tab, above or replacing the current static `most_active_times.png`.
- Filterable by person (person filter already wired up).
- Add to `charts_payloads.py` as a new key in the dashboard-data response.

---

### 3B — Per-Person Sentiment Trends

The current `sentiment.png` static chart shows global sentiment. An interactive version with per-person lines would reveal who drives positivity/negativity spikes.

- Use TextBlob polarity scores already computed during graph generation; move or re-compute into the analyzer pipeline.
- Monthly average polarity per person → multi-line Plotly chart in the **Activity** or **Topics** tab.
- Add a "Mood summary" stat card in the Overview tab: most positive / most negative participant.

---

### 3C — Response Time Distribution (Violin / Box Plot)

The current **Activity** tab shows average response times as a heatmap. Adding a violin or box plot of the *distribution* of response times per person (or per pair) reveals outliers: does person A usually reply in 2 minutes but occasionally ghost for days?

- Use the same `(prev_person, curr_person, delta_minutes)` tuples already computed in `response_patterns.py`.
- Cap the x-axis at e.g. 24h to keep the chart readable.
- Add to the **Activity** tab.

---

### 3D — Per-Person Word Clouds

The current word cloud is global. Generate one per participant as small individual panels in the **Topics** tab. Use `matplotlib`'s `WordCloud` (already a dependency) with a different colormap per person.

- Server-side: generate `wordcloud_<person>.png` at analysis time, embed base64 in the dashboard-data or serve as static files.
- Client-side: render a row of `<img>` tags, one per person, with name labels.

---

### 3E — Conversation Ghosting / Unanswered Messages

Detect messages that were the last in a conversation window (defined by the 1-hour gap already used in `response_patterns.py`) and were never replied to. Per-person count and percentage of "ignored last messages."

- This is a relationship-level signal: a one-way chat where one person rarely replies to the other's final messages.
- Surface in the **Relationships** tab as a bar chart ("unanswered conversation-enders") or add to the two-person balance panel.

---

### 3F — Vocabulary Richness (Type-Token Ratio)

A simple per-person metric: unique words / total words. High TTR = more varied vocabulary; low TTR = repetitive. Useful and fun for group chats.

- Compute in the topics analyzer or a new `text_stats.py` module.
- Show as a stat card in the Overview tab or a bar chart in the Topics tab.

---

### 3G — Question-Asking Patterns

Count messages ending in `?` per person; compute "question rate" (questions / total messages). Who drives the conversation by asking questions vs. who makes statements?

- Pure string analysis on the `messages` table; no new dependency.
- Show in Overview as a stat card or in Activity as a horizontal bar chart.

---

### 3H — Monthly Participation Bump Chart

A "race chart" showing the ranking of participants by monthly message count over time. Each participant is a line; the y-axis is rank (1 = most active that month). Shows shifts in who dominates the chat.

- Data already available from the `messages` table.
- Plotly line chart with reversed y-axis, one line per person.
- Add to the **Activity** tab.

---

### 3I — Longest Silence Periods

Calculate the time gaps between consecutive messages; surface the top 10 longest silences (gap start datetime, gap end datetime, duration in hours/days). Could indicate real-world events (vacation, conflict, major life event).

- Add to the **Activity** tab as an annotated timeline or a simple sorted table.
- Very low computation cost; pure pandas diff on datetime index.

---

### 3J — Late-Night and Weekend Activity Breakdown

Per-person counts and rates for:

- "Night owl" messages: sent between 22:00–04:00
- Weekend messages: Saturday and Sunday

Surface as small stat cards in the Overview tab or a grouped bar chart in Activity.

---

## 4. Other Improvements

### 4A — Dark / Light Theme Toggle

Already on the TODO list. Implementation notes:

- CSS custom properties (`--bg`, `--text`, `--card-bg`, etc.) on `:root` with a `.dark` class on `<body>`.
- `localStorage.getItem('theme')` to persist preference; `prefers-color-scheme` media query for initial default.
- One small toggle button in the navbar (moon/sun icon, `<button>` with `aria-label`).
- Plotly charts: re-call `Plotly.relayout(div, { paper_bgcolor, plot_bgcolor, font: { color } })` on theme switch.

---

### 4B — Better Upload Error Handling

Currently the upload page shows "Processing…" and then either redirects or (on parser failure) likely throws a 500. Add:

- Server-side: catch parse errors; return a proper error page/flash message with a human-readable explanation ("No WhatsApp messages detected in this file. Make sure you export the chat as a .txt file from WhatsApp.").
- Client-side: detect the redirect vs. error response; show a clear error state with a retry button.
- Add format detection feedback: after successful upload, display which parser format was detected ("Parsed as: Dutch DD-MM-YYYY format, 1,243 messages, language: nl").

---

### 4C — Upload Progress for Large Files

For chats with 50k+ messages, the analysis takes several seconds. The current "Processing…" message gives no sense of progress. Options:

- **Simple**: compute analysis server-side, show a spinner with elapsed time (JS `setInterval` counter).
- **Better**: use Server-Sent Events (`/api/progress/<job_id>`) to stream progress steps ("Parsing... Analyzing topics... Generating charts..."). Flask supports SSE natively with `Response(stream_with_context(...))`. No additional dependencies.
- **Full async**: background worker (Celery or `threading`) with a `/status/<job_id>` polling endpoint. Higher complexity, only worth it for very large files.

---

### 4D — Named Sessions / Session Management

Allow users to label their analyses with a friendly name:

- Add a `name` column to the `chats` table (nullable, defaults to `source_name`).
- In the recent-sessions list, show an inline-editable name field.
- `PATCH /api/chat/<id>` to update the name.
- Add a `DELETE /api/chat/<id>` route with confirmation prompt to remove old analyses and free disk space.

---

### 4E — Onboarding: How to Export a WhatsApp Chat

New users often don't know how to get a `.txt` export. Add a collapsible "How to export" section on `upload.html`:

```
WhatsApp (Android): Chat → ⋮ menu → More → Export chat → Without media → share .txt file
WhatsApp (iPhone):  Chat → contact name → Export Chat → Without Media → share .txt file
```

A three-step illustration (screenshot or SVG icon sequence) would reduce friction significantly for non-technical users.

---

### 4F — Person Name Aliasing / Merging

In group chats, the same person may appear under multiple names (phone number vs. saved contact, name change over time). Add a UI on the dashboard to merge two person labels into one:

- `POST /api/chat/<chat_id>/merge-persons` with `{ from: "...", to: "..." }` body.
- Updates the `messages` table (`UPDATE messages SET person = ? WHERE chat_id = ? AND person = ?`).
- Invalidates and re-runs the analyzer cache for that chat.
- Show in the Overview tab as a small "Manage participants" link.

---

### 4G — Remove Deprecated Wrappers

The `wa-stats.py`, `wa-stats-flask.py`, `wa-graphs.py`, and `wa-flask.py` files have been printing deprecation warnings for at least one full session cycle. Set a removal milestone (e.g. "next major cleanup commit") and delete them. Update `README.md` and `AGENTS.md` accordingly.

---

### 4H — Date Storage Cleanup

Dates are currently stored as `DD-MM-YYYY` strings in the `messages` table. The date-range filtering in `get_chat_context()` does string rearrangement inside SQLite (`substr`) to sort correctly — fragile and hard to query. Migrate to ISO-8601 (`YYYY-MM-DD`) strings (sortable lexicographically) or SQLite `DATE` type. This is a one-time migration with a schema change + data re-write.

---

### 4I — LLM Integration (Phase 6 activation)

The structure is already in place. The lowest-effort, highest-fun activation is the "snarky commentary" pattern from `docs/llm-integration.md`:

1. After dashboard data loads, fetch `/api/chat/<id>/context` (already returns structured stats).
2. POST to a configurable LLM endpoint with a prompt like: *"Given these WhatsApp chat stats, write 2–3 funny, slightly snarky observations about the participants. Stats: {context}"*
3. Display the response as a styled "AI commentary" card in the Overview tab.
4. Gate behind a `KAAJD_LLM_ENABLED=true` env var and a UI toggle.

This requires no new data infrastructure — only activating the `LLM_ENDPOINT_URL` config already present in `config.py`.

---

## Priority Matrix

| Item | Effort | Impact | Suggested Order |
|------|--------|--------|----------------|
| Day×Hour heatmap (3A) | Low | High | 1 |
| Load previous sessions (1A) | Low | High | 2 |
| Per-chart PNG download (2B) | Low | Medium | 3 |
| Dark/light theme toggle (4A) | Low | Medium | 4 |
| Sample/demo data (1B) | Low | Medium | 5 |
| Upload error handling (4B) | Low | Medium | 6 |
| Onboarding export guide (4E) | Very Low | High | 7 |
| Mobile tab overflow fix (2A) | Low | High | 8 |
| Response time distribution (3C) | Low | Medium | 9 |
| ZIP export (2D) | Low | Medium | 10 |
| PDF report (2C) | Medium | High | 11 |
| Per-person word clouds (3D) | Medium | Medium | 12 |
| Sentiment per person (3B) | Medium | Medium | 13 |
| Named sessions (4D) | Medium | Medium | 14 |
| Vocabulary richness (3F) | Low | Low | 15 |
| Question patterns (3G) | Low | Low | 16 |
| Participation bump chart (3H) | Medium | Medium | 17 |
| Upload progress SSE (4C) | Medium | Medium | 18 |
| Silence periods (3I) | Low | Medium | 19 |
| Ghosting detection (3E) | Medium | Medium | 20 |
| Person aliasing (4F) | High | Low | 21 |
| LLM integration (4I) | Medium | High (fun) | 22 |
| Remove deprecated wrappers (4G) | Low | Low | 23 |
| Date storage cleanup (4H) | Medium | Low | 24 |
| PWA manifest (2A) | Low | Low | 25 |
