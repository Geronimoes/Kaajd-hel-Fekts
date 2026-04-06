from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd


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
    if raw_data_df.empty:
        return {
            "day_hour_heatmap": {
                "x": [str(hour) for hour in range(24)],
                "y": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "z": [[0 for _ in range(24)] for _ in range(7)],
            }
        }

    activity_df = raw_data_df.copy()
    if "IsSystemMessage" in activity_df.columns:
        activity_df = activity_df[~activity_df["IsSystemMessage"]]

    if activity_df.empty:
        return {
            "day_hour_heatmap": {
                "x": [str(hour) for hour in range(24)],
                "y": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "z": [[0 for _ in range(24)] for _ in range(7)],
            }
        }

    activity_df["DateTime"] = pd.to_datetime(
        activity_df["Date"].astype(str) + " " + activity_df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    activity_df = activity_df[activity_df["DateTime"].notna()]

    weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hour_labels = [str(hour) for hour in range(24)]
    if activity_df.empty:
        return {
            "day_hour_heatmap": {
                "x": hour_labels,
                "y": weekday_labels,
                "z": [[0 for _ in range(24)] for _ in range(7)],
            }
        }

    activity_df["Weekday"] = activity_df["DateTime"].dt.weekday
    activity_df["Hour"] = activity_df["DateTime"].dt.hour
    matrix = activity_df.groupby(["Weekday", "Hour"]).size().unstack(fill_value=0)
    matrix = matrix.reindex(index=range(7), fill_value=0)
    matrix = matrix.reindex(range(24), axis=1, fill_value=0)

    return {
        "day_hour_heatmap": {
            "x": hour_labels,
            "y": weekday_labels,
            "z": matrix.values.tolist(),
        }
    }


def _response_patterns_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    response_pairs = analysis.get("response_pairs", [])
    response_delays = analysis.get("response_delay_distribution", [])
    starters = analysis.get("conversation_starters", [])

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
        capped_values = [min(value, 24 * 60) for value in values]
        distribution_traces.append(
            {
                "name": person,
                "y": capped_values,
            }
        )

    return {
        "response_time_heatmap": {
            "x": heatmap_people,
            "y": heatmap_people,
            "z": z,
        },
        "response_time_distribution": {
            "traces": distribution_traces,
            "max_minutes_cap": 24 * 60,
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

    month_person_media: dict[tuple[str, str], int] = defaultdict(int)
    month_person_links: dict[tuple[str, str], int] = defaultdict(int)
    months: set[str] = set()
    people: set[str] = set()
    for row in monthly:
        month = str(row.get("Month", ""))
        person = str(row.get("Person", ""))
        if not month or not person:
            continue
        months.add(month)
        people.add(person)
        month_person_media[(month, person)] = int(row.get("media_messages", 0))
        month_person_links[(month, person)] = int(row.get("link_messages", 0))

    sorted_months = sorted(months)
    sorted_people = sorted(people)
    traces = []
    for person in sorted_people:
        traces.append(
            {
                "name": f"{person} media",
                "x": sorted_months,
                "y": [month_person_media[(month, person)] for month in sorted_months],
                "series": "media",
                "person": person,
            }
        )
        traces.append(
            {
                "name": f"{person} links",
                "x": sorted_months,
                "y": [month_person_links[(month, person)] for month in sorted_months],
                "series": "links",
                "person": person,
            }
        )

    return {
        "per_person_stacked": {
            "x": [item.get("person") for item in per_person],
            "media": [item.get("media_messages", 0) for item in per_person],
            "links": [item.get("link_messages", 0) for item in per_person],
            "text": [item.get("text_messages", 0) for item in per_person],
        },
        "top_domains_bar": {
            "x": [item.get("domain") for item in domains],
            "y": [item.get("count", 0) for item in domains],
        },
        "monthly_traces": traces,
    }


def _topics_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    topics = analysis.get("topics", [])
    monthly_trends = analysis.get("monthly_trends", [])

    topic_labels = []
    topic_terms = []
    for topic in topics:
        label = f"Topic {topic.get('topic_id')}"
        terms = [term.get("term") for term in topic.get("top_terms", [])]
        topic_labels.append(label)
        topic_terms.append(terms)

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
        },
        "monthly_trend_rows": trend_rows,
    }


def _relationships_payload(analysis: dict[str, Any]) -> dict[str, Any]:
    affinity = analysis.get("affinity_scores", [])
    correlations = analysis.get("activity_correlations", [])

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
            "x": people,
            "y": people,
            "z": affinity_z,
        },
        "correlation_heatmap": {
            "x": corr_people,
            "y": corr_people,
            "z": corr_z,
        },
        "two_person_balance": analysis.get("two_person_balance"),
    }
