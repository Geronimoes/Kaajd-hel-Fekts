# Kaajd Chart Review

This document provides a detailed critique of the generated charts found in the `/sample` directory. 

## General Observations

There appears to be a mix of two rendering styles in the project:
1. **Legacy Matplotlib Charts:** (e.g., `conversation_starters.png`, `messages_over_time.png`, `top_emojis.png`) - These have a dated aesthetic, basic styling, and often suffer from text-overlapping issues.
2. **Newer Plotly Charts:** (e.g., `kaajd-*.png`) - These look much more modern, clean, and interactive-friendly. However, many of them suffer from a lack of explicit axis titles.

---

## Detailed Chart Critique

### 1. Topic & Content Analysis

**`kaajd-topic-labels.png`**
*   **Critique:** This is arguably the weakest visualization. It attempts to display topics by rendering horizontal text inside vertical bars. 
*   **Issues:** The bars seem to have arbitrary, ascending heights that don't map to a clear metric. The text rendering is broken (e.g., Topic 5's text is rendered vertically and spills out of the chart). 
*   **Recommendation:** Do not use a bar chart to display lists of words unless the X-axis is the word and the Y-axis is its weight/score. A horizontal bar chart of the top 10 terms overall, or a stylized table/grid for topics, would be much more effective.

**`top_emojis.png` (Matplotlib)**
*   **Critique:** Displays a bar chart of emoji frequencies.
*   **Issues:** There is a severe bug in the data parsing or labeling. Some labels repeat endlessly (e.g., `"rolling on the floor laughingrolling on the floor laughing..."`), which breaks the X-axis layout. Furthermore, using the CLDR text names of emojis is much harder to read at a glance than the actual emojis.
*   **Recommendation:** Fix the text concatenation bug. Ideally, render the actual Unicode emojis on the X-axis or next to horizontal bars. Update this to the Plotly styling.

**`wordcloud.png`**
*   **Critique:** A standard word cloud. 
*   **Issues:** It provides a general vibe but lacks precision. Some of the most prominent words are arguably conversational filler in Dutch ("echt", "net", "gewoon", "jullie").
*   **Recommendation:** Ensure custom stop words are aggressively tuned for conversational Dutch to surface more meaningful nouns and entities.

**`sentiment.png` (Matplotlib)**
*   **Critique:** Plots sentiment polarity over time using "Message Index" on the X-axis.
*   **Issues:** Because it plots *every single message*, it is extremely noisy ("heartbeat" aesthetic) and impossible to read. The red "Trend" line is completely flat at ~0.0 because the noise averages out. Using "Message Index" instead of a Date makes it impossible to correlate sentiment with real-world events.
*   **Recommendation:** Aggregate sentiment scores by day, week, or month, and plot those averages over a Date X-axis. Switch to Plotly styling.

### 2. Time & Activity

**`messages_over_time.png` (Matplotlib)**
*   **Critique:** A scatter plot with a trendline showing message frequency.
*   **Issues:** It looks like a scatter plot where the Y-axis is daily message count, but the dots form vertical stripes, making it look very messy. 
*   **Recommendation:** A bar chart or an area chart aggregated by week or month would be vastly superior for showing volume over time.

**`most_active_times.png` (Matplotlib)**
*   **Critique:** A line chart showing activity by hour, split by quarters of the year.
*   **Issues:** While interesting, it's quite busy and the styling is dated. The overall shape across quarters seems fairly consistent, making the split slightly redundant.
*   **Recommendation:** The `kaajd-day-hour-activity.png` heatmap does a much better job of showing this data. If keeping this line chart, upgrade to Plotly and perhaps use a smoothed area chart.

**`kaajd-day-hour-activity.png`**
*   **Critique:** Excellent visualization. The heatmap perfectly captures the intersection of days and hours.
*   **Recommendation:** Keep as is. It's clear and effective.

### 3. Response Patterns

**`kaajd-response-time-distribution.png`**
*   **Critique:** A violin/strip plot of response times in minutes.
*   **Issues:** The Y-axis scales up to 1400+ minutes (over 23 hours), causing the vast majority of the data (which happens in the first few minutes/hours) to be squished flat at the very bottom. The violin outlines are completely flattened.
*   **Recommendation:** Use a logarithmic scale for the Y-axis, or strictly cap/filter the outliers (e.g., only show responses under 4 hours) to make the core distribution visible.

**`kaajd-response-heatmap.png` & `kaajd-affinity-heatmap.png`**
*   **Critique:** Good use of heatmaps for pairwise metrics.
*   **Issues:** They lack explicit X and Y axis titles (e.g., "Responder" vs "Sender"), which forces the user to guess how to read the matrix (Row responds to Column, or Column responds to Row?). The white blocks in the response heatmap (likely representing NaN/No Data) are a bit jarring against the Viridis color scale.
*   **Recommendation:** Add clear axis titles. Use a distinct, muted color (like light gray or crosshatching) for missing data so it isn't confused with a high/low value on a light color scale.

### 4. Media & Links

**`kaajd-media-links-per-person.png`**
*   **Critique:** Stacked bar chart showing Links vs Media per person.
*   **Issues:** Very clean, but lacks a Y-axis title ("Number of Messages"). 
*   **Recommendation:** Add Y-axis title.

**`kaajd-media-monthly-trends.png`**
*   **Critique:** A line chart plotting media and links per person over time.
*   **Issues:** This is a classic "spaghetti chart". With 6+ people, each having 2 lines (media and links), there are over 12 lines crisscrossing. It is unreadable and impossible to derive insights from.
*   **Recommendation:** Simplify this entirely. Either plot the *total* group media/links over time, or use a stacked area chart, or use "small multiples" (facets) to give each person their own small chart.

**`kaajd-top-shared-domains.png`**
*   **Critique:** Clean bar chart of domains.
*   **Issues:** Lacks a Y-axis title. `youtube.com` and `youtu.be` are tracked separately, which splits the actual impact of YouTube links.
*   **Recommendation:** Add Y-axis title. Add a data-cleaning step to normalize common link shorteners (e.g., map `youtu.be` to `youtube.com`) before plotting.

### 5. Participant Stats

**`conversation_starters.png` vs `kaajd-conversation-starters.png`**
*   **Critique:** The Plotly version is much cleaner but removes the axis titles present in the Matplotlib version.
*   **Issues:** In the Plotly version, the long name "Simon Vier Jansen Kassa Vier Alstublieft" forces the chart to allocate too much space for labels or overlap them if window size shrinks.
*   **Recommendation:** Use the Plotly version but add axis titles back. Introduce name truncation (e.g., "Simon Vier Jansen K...") for the X-axis labels to keep the chart tidy.