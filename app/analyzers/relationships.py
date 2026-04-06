from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from statistics import mean
from typing import Any

import pandas as pd


def analyze_relationships(raw_data_df: pd.DataFrame) -> dict[str, Any]:
    if raw_data_df.empty:
        return _empty_result()

    df = raw_data_df.copy()
    if "IsSystemMessage" in df.columns:
        df = df[~df["IsSystemMessage"]]
    if df.empty:
        return _empty_result()

    df["Person"] = df["Person"].fillna("").astype(str)
    df = df[df["Person"].str.strip() != ""]
    if df.empty:
        return _empty_result()

    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    df = df.dropna(subset=["Datetime"]).copy()
    if df.empty:
        return _empty_result()

    df = df.sort_values("Datetime").reset_index(drop=True)
    participants = sorted(df["Person"].unique().tolist())

    affinity_scores = _compute_affinity_scores(df)
    activity_correlations = _compute_activity_correlations(df, participants)
    two_person_balance = _compute_two_person_balance(df, participants)

    return {
        "participants": participants,
        "is_two_person_chat": len(participants) == 2,
        "affinity_scores": affinity_scores,
        "activity_correlations": activity_correlations,
        "two_person_balance": two_person_balance,
    }


def _compute_affinity_scores(df: pd.DataFrame) -> list[dict[str, Any]]:
    transitions: dict[tuple[str, str], int] = defaultdict(int)
    outgoing_total: dict[str, int] = defaultdict(int)

    previous_person: str | None = None
    for row in df.itertuples(index=False):
        person = str(row.Person)
        if previous_person is not None and previous_person != person:
            transitions[(previous_person, person)] += 1
            outgoing_total[previous_person] += 1
        previous_person = person

    output: list[dict[str, Any]] = []
    for (from_person, to_person), count in sorted(transitions.items()):
        base = outgoing_total.get(from_person, 0)
        affinity = round((count / base), 4) if base else 0.0
        output.append(
            {
                "from": from_person,
                "to": to_person,
                "replies": int(count),
                "from_total_replies": int(base),
                "affinity_score": affinity,
            }
        )
    return output


def _compute_activity_correlations(
    df: pd.DataFrame, participants: list[str]
) -> list[dict[str, Any]]:
    daily_df = df.copy()
    daily_df["Day"] = daily_df["Datetime"].dt.date

    pivot = (
        daily_df.groupby(["Day", "Person"]).size().unstack(fill_value=0).sort_index()
    )
    for person in participants:
        if person not in pivot.columns:
            pivot[person] = 0
    pivot = pivot[participants]

    output: list[dict[str, Any]] = []
    for person_a, person_b in combinations(participants, 2):
        series_a = pivot[person_a]
        series_b = pivot[person_b]
        if len(series_a) < 2:
            correlation = None
        else:
            corr_value = series_a.corr(series_b)
            correlation = round(float(corr_value), 4) if pd.notna(corr_value) else None

        output.append(
            {
                "person_a": person_a,
                "person_b": person_b,
                "pearson_correlation": correlation,
                "days_compared": int(len(series_a)),
            }
        )

    return sorted(
        output,
        key=lambda item: (
            item["pearson_correlation"] is None,
            -(item["pearson_correlation"] or -999.0),
        ),
    )


def _compute_two_person_balance(
    df: pd.DataFrame, participants: list[str]
) -> dict[str, Any] | None:
    if len(participants) != 2:
        return None

    person_a, person_b = participants
    gap_threshold = pd.Timedelta(hours=1)

    conversations: list[pd.DataFrame] = []
    start_idx = 0
    for idx in range(1, len(df)):
        if df.loc[idx, "Datetime"] - df.loc[idx - 1, "Datetime"] > gap_threshold:
            conversations.append(df.iloc[start_idx:idx])
            start_idx = idx
    conversations.append(df.iloc[start_idx:])

    starts = {person_a: 0, person_b: 0}
    response_times: dict[tuple[str, str], list[float]] = defaultdict(list)

    for convo in conversations:
        if convo.empty:
            continue
        starter = str(convo.iloc[0]["Person"])
        if starter in starts:
            starts[starter] += 1

        for idx in range(1, len(convo)):
            previous = convo.iloc[idx - 1]
            current = convo.iloc[idx]
            prev_person = str(previous["Person"])
            curr_person = str(current["Person"])
            if prev_person == curr_person:
                continue
            delta_min = (
                current["Datetime"] - previous["Datetime"]
            ).total_seconds() / 60.0
            if delta_min >= 0:
                response_times[(prev_person, curr_person)].append(delta_min)

    total_starts = starts[person_a] + starts[person_b]
    initiative_share = {
        person_a: round(starts[person_a] / total_starts, 4) if total_starts else 0.0,
        person_b: round(starts[person_b] / total_starts, 4) if total_starts else 0.0,
    }

    avg_a_to_b = (
        mean(response_times[(person_a, person_b)])
        if response_times[(person_a, person_b)]
        else None
    )
    avg_b_to_a = (
        mean(response_times[(person_b, person_a)])
        if response_times[(person_b, person_a)]
        else None
    )

    asymmetry = None
    if avg_a_to_b is not None and avg_b_to_a is not None:
        asymmetry = round(avg_a_to_b - avg_b_to_a, 3)

    return {
        "participants": [person_a, person_b],
        "conversation_starts": {
            person_a: int(starts[person_a]),
            person_b: int(starts[person_b]),
        },
        "initiative_share": initiative_share,
        "avg_response_minutes": {
            f"{person_a}_to_{person_b}": round(avg_a_to_b, 3)
            if avg_a_to_b is not None
            else None,
            f"{person_b}_to_{person_a}": round(avg_b_to_a, 3)
            if avg_b_to_a is not None
            else None,
        },
        "response_time_asymmetry_minutes": asymmetry,
        "conversation_count": int(total_starts),
    }


def _empty_result() -> dict[str, Any]:
    return {
        "participants": [],
        "is_two_person_chat": False,
        "affinity_scores": [],
        "activity_correlations": [],
        "two_person_balance": None,
    }
