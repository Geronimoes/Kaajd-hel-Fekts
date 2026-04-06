from __future__ import annotations

from collections import defaultdict
from typing import Any
import emoji

import pandas as pd

BOT_PARTICIPANTS = {"meta ai"}


def _truncate(name: str, max_len: int = 22) -> str:
    return name if len(name) <= max_len else name[: max_len - 1] + "…"


def build_plotly_payloads(
    *,
    raw_data_df: pd.DataFrame,
    response_patterns: dict[str, Any],
    media_links: dict[str, Any],
    topics: dict[str, Any],
    relationships: dict[str, Any],
) -> dict[str, Any]:
    return {
        "activity": _activity_payload(raw_data_df),
        "response_patterns": _response_patterns_payload(response_patterns),
        "media_links": _media_links_payload(media_links),
        "topics": _topics_payload(topics),
        "relationships": _relationships_payload(relationships),
    }


def _activity_payload(raw_data_df: pd.DataFrame) -> dict[str, Any]:
    empty_payload = {
        "day_hour_heatmap": {
            "x": [str(hour) for hour in range(24)],
            "y": ["Sun", "Sat", "Fri", "Thu", "Wed", "Tue", "Mon"],
            "z": [[0 for _ in range(24)] for _ in range(7)],
        },
        "monthly_volume": {"x": [], "y": []},
        "message_length": [],
        "emojis_overall": {"x": [], "y": []},
        "emojis_per_person": {},
        "monthly_rank": [],
    }

    if raw_data_df.empty:
        return empty_payload

    activity_df = raw_data_df.copy()
    if "IsSystemMessage" in activity_df.columns:
        activity_df = activity_df[~activity_df["IsSystemMessage"]]

    if activity_df.empty:
        return empty_payload

    activity_df["DateTime"] = pd.to_datetime(
        activity_df["Date"].astype(str) + " " + activity_df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    activity_df = activity_df.dropna(subset=["DateTime"])

    if activity_df.empty:
        return empty_payload

    # Heatmap
    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hour_labels = [str(hour) for hour in range(24)]

    activity_df["Weekday"] = activity_df["DateTime"].dt.weekday
    activity_df["Hour"] = activity_df["DateTime"].dt.hour
    matrix = activity_df.groupby(["Weekday", "Hour"]).size().unstack(fill_value=0)
    matrix = matrix.reindex(index=range(7), fill_value=0)
    matrix = matrix.reindex(range(24), axis=1, fill_value=0)

    # Reverse to make Sun at top (index 6 goes to 0) -> [Sun, Sat, Fri, Thu, Wed, Tue, Mon]
    z_heatmap = matrix.values.tolist()
    z_heatmap_reversed = list(reversed(z_heatmap))
    y_labels_reversed = list(reversed(weekday_labels))

    # Monthly volume
    activity_df["Month"] = activity_df["DateTime"].dt.to_period("M").astype(str)
    monthly_counts = activity_df.groupby("Month").size().reset_index(name="Count")
    monthly_volume = {
        "x": monthly_counts["Month"].tolist(),
        "y": monthly_counts["Count"].tolist(),
    }

    # Message length distribution per person
    activity_df["Person"] = activity_df["Person"].fillna("").astype(str)
    people_lengths = defaultdict(list)
    for row in activity_df.itertuples():
        person = row.Person.strip()
        if person:
            people_lengths[person].append(len(str(row.Message)))

    message_length_traces = []
    for p, lengths in sorted(people_lengths.items()):
        message_length_traces.append({"name": p, "y": lengths})

    # Emojis
    def extract_emojis(msg: str):
        return [item["emoji"] for item in emoji.emoji_list(str(msg))]

    activity_df["Emojis"] = activity_df["Message"].apply(extract_emojis)
    all_emojis_list = sum(activity_df["Emojis"], [])
    emoji_counts = pd.Series(all_emojis_list).value_counts().head(10)
    emojis_overall = {
        "x": emoji_counts.index.tolist(),
        "y": emoji_counts.values.tolist(),
    }

    emojis_per_person = {}
    for person in sorted(people_lengths.keys()):
        person_emojis = sum(activity_df[activity_df["Person"] == person]["Emojis"], [])
        if person_emojis:
            top_3 = pd.Series(person_emojis).value_counts().head(3)
            emojis_per_person[person] = {
                "x": top_3.index.tolist(),
                "y": top_3.values.tolist(),
            }

    # Monthly Rank (Bump Chart)
    # Ranks 1 = most active.
    monthly_rank_traces = []
    if not activity_df.empty:
        person_month_counts = (
            activity_df.groupby(["Month", "Person"]).size().reset_index(name="Count")
        )
        # Sort by month and then count desc
        person_month_counts = person_month_counts.sort_values(
            by=["Month", "Count"], ascending=[True, False]
        )
        # Assign rank
        person_month_counts["Rank"] = person_month_counts.groupby("Month")[
            "Count"
        ].rank(method="min", ascending=False)

        for person in person_month_counts["Person"].unique():
            person_data = person_month_counts[person_month_counts["Person"] == person]
            monthly_rank_traces.append(
                {
                    "name": person,
                    "x": person_data["Month"].tolist(),
                    "y": person_data["Rank"].tolist(),
                }
            )

    return {
        "day_hour_heatmap": {
            "x": hour_labels,
            "y": y_labels_reversed,
            "z": z_heatmap_reversed,
        },
        "monthly_volume": monthly_volume,
        "message_length": message_length_traces,
        "emojis_overall": emojis_overall,
        "emojis_per_person": emojis_per_person,
        "monthly_rank": monthly_rank_traces,
    }


def _response_patterns_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    response_pairs = analysis.get("response_pairs", [])
    response_delays = analysis.get("response_delay_distribution", [])
    starters = analysis.get("conversation_starters", [])

    response_pairs = [
        p
        for p in response_pairs
        if str(p.get("from")).lower() not in BOT_PARTICIPANTS
        and str(p.get("to")).lower() not in BOT_PARTICIPANTS
    ]
    response_delays = [
        d
        for d in response_delays
        if str(d.get("person")).lower() not in BOT_PARTICIPANTS
    ]
    starters = [
        s for s in starters if str(s.get("person")).lower() not in BOT_PARTICIPANTS
    ]
    starters = sorted(
        starters, key=lambda x: x.get("conversations_started", 0), reverse=True
    )

    heatmap_people = sorted(
        {pair.get("from") for pair in response_pairs if pair.get("from")}
        | {pair.get("to") for pair in response_pairs if pair.get("to")}
    )

    matrix = {
        from_person: {to_person: None for to_person in heatmap_people}
        for from_person in heatmap_people
    }
    for pair in response_pairs:
        from_person = pair.get("from")
        to_person = pair.get("to")
        if from_person in matrix and to_person in matrix[from_person]:
            matrix[from_person][to_person] = pair.get("avg_response_minutes")

    z = [[matrix[row][col] for col in heatmap_people] for row in heatmap_people]

    per_person_distribution: dict[str, list[float]] = defaultdict(list)
    for delay_row in response_delays:
        person = str(delay_row.get("person") or "").strip()
        minutes_raw = delay_row.get("response_minutes")
        if not person or minutes_raw is None:
            continue
        try:
            minutes = float(minutes_raw)
        except (TypeError, ValueError):
            continue
        if minutes < 0:
            continue
        per_person_distribution[person].append(minutes)

    distribution_traces = []
    for person, values in sorted(per_person_distribution.items()):
        capped_values = [min(value, 240) for value in values]  # Cap at 4 hours
        distribution_traces.append(
            {
                "name": person,
                "y": capped_values,
            }
        )

    return {
        "response_time_heatmap": {
            "x": [_truncate(p) for p in heatmap_people],
            "y": [_truncate(p) for p in heatmap_people],
            "z": z,
        },
        "response_time_distribution": {
            "traces": distribution_traces,
            "max_minutes_cap": 240,
        },
        "conversation_starters_bar": {
            "x": [item.get("person") for item in starters],
            "y": [item.get("conversations_started", 0) for item in starters],
            "avg_len": [
                item.get("avg_conversation_length_messages") for item in starters
            ],
        },
    }


def _media_links_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    per_person = analysis.get("per_person", [])
    domains = analysis.get("top_domains", [])
    monthly = analysis.get("by_month", [])

    month_media: dict[str, int] = defaultdict(int)
    month_links: dict[str, int] = defaultdict(int)
    months: set[str] = set()
    for row in monthly:
        month = str(row.get("Month", ""))
        if not month:
            continue
        months.add(month)
        month_media[month] += int(row.get("media_messages", 0))
        month_links[month] += int(row.get("link_messages", 0))

    sorted_months = sorted(months)

    traces = [
        {
            "name": "Media",
            "x": sorted_months,
            "y": [month_media[month] for month in sorted_months],
        },
        {
            "name": "Links",
            "x": sorted_months,
            "y": [month_links[month] for month in sorted_months],
        },
    ]

    top_15_domains = domains[:15]

    return {
        "per_person_stacked": {
            "x": [item.get("person") for item in per_person],
            "media": [item.get("media_messages", 0) for item in per_person],
            "links": [item.get("link_messages", 0) for item in per_person],
            "text": [item.get("text_messages", 0) for item in per_person],
        },
        "top_domains_bar": {
            "x": [item.get("domain") for item in top_15_domains],
            "y": [item.get("count", 0) for item in top_15_domains],
        },
        "monthly_traces": traces,
    }


def _topics_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    topics = analysis.get("topics", [])
    monthly_trends = analysis.get("monthly_trends", [])

    topic_labels = []
    topic_terms = []
    topic_weights = []
    for topic in topics:
        label = f"Topic {topic.get('topic_id')}"
        terms = [term.get("term") for term in topic.get("top_terms", [])]
        weights = [term.get("weight") for term in topic.get("top_terms", [])]
        topic_labels.append(label)
        topic_terms.append(terms)
        topic_weights.append(weights)

    trend_rows = []
    for row in monthly_trends:
        month = row.get("month")
        top_terms = row.get("top_terms", [])
        trend_rows.append(
            {
                "month": month,
                "terms": [item.get("term") for item in top_terms],
                "scores": [item.get("score") for item in top_terms],
            }
        )

    return {
        "topic_terms": {
            "labels": topic_labels,
            "terms": topic_terms,
            "weights": topic_weights,
        },
        "monthly_trend_rows": trend_rows,
    }


def _relationships_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    affinity = analysis.get("affinity_scores", [])
    correlations = analysis.get("activity_correlations", [])

    affinity = [
        row
        for row in affinity
        if str(row.get("from")).lower() not in BOT_PARTICIPANTS
        and str(row.get("to")).lower() not in BOT_PARTICIPANTS
    ]
    correlations = [
        row
        for row in correlations
        if str(row.get("person_a")).lower() not in BOT_PARTICIPANTS
        and str(row.get("person_b")).lower() not in BOT_PARTICIPANTS
    ]

    people = sorted(
        {row.get("from") for row in affinity if row.get("from")}
        | {row.get("to") for row in affinity if row.get("to")}
    )

    affinity_map = {a: {b: 0.0 for b in people} for a in people}
    for row in affinity:
        from_person = row.get("from")
        to_person = row.get("to")
        if from_person in affinity_map and to_person in affinity_map[from_person]:
            affinity_map[from_person][to_person] = row.get("affinity_score", 0.0)
    affinity_z = [[affinity_map[row][col] for col in people] for row in people]

    corr_people = sorted(
        {row.get("person_a") for row in correlations if row.get("person_a")}
        | {row.get("person_b") for row in correlations if row.get("person_b")}
    )
    corr_map: dict[str, dict[str, float]] = {
        a: {b: 0.0 for b in corr_people} for a in corr_people
    }
    for person in corr_people:
        corr_map[person][person] = 1.0
    for row in correlations:
        a = row.get("person_a")
        b = row.get("person_b")
        raw_value = row.get("pearson_correlation")
        value = float(raw_value) if raw_value is not None else 0.0
        if a in corr_map and b in corr_map[a]:
            corr_map[a][b] = value
            corr_map[b][a] = value
    corr_z = [[corr_map[row][col] for col in corr_people] for row in corr_people]

    return {
        "affinity_heatmap": {
            "x": [_truncate(p) for p in people],
            "y": [_truncate(p) for p in people],
            "z": affinity_z,
        },
        "correlation_heatmap": {
            "x": [_truncate(p) for p in corr_people],
            "y": [_truncate(p) for p in corr_people],
            "z": corr_z,
        },
        "two_person_balance": analysis.get("two_person_balance"),
    }
