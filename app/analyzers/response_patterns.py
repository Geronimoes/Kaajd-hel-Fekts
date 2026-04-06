from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

import pandas as pd


def analyze_response_patterns(raw_data_df: pd.DataFrame) -> dict[str, Any]:
    if raw_data_df.empty:
        return {
            "response_pairs": [],
            "response_delay_distribution": [],
            "reply_matrix": {},
            "conversation_starters": [],
            "conversation_summary": {
                "total_conversations": 0,
                "overall_avg_conversation_length_messages": 0.0,
            },
        }

    df = raw_data_df.copy()
    if "IsSystemMessage" in df.columns:
        df = df[~df["IsSystemMessage"]]
    if df.empty:
        return {
            "response_pairs": [],
            "response_delay_distribution": [],
            "reply_matrix": {},
            "conversation_starters": [],
            "conversation_summary": {
                "total_conversations": 0,
                "overall_avg_conversation_length_messages": 0.0,
            },
        }

    df["Person"] = df["Person"].fillna("").astype(str)
    df = df[df["Person"].str.strip() != ""]
    if df.empty:
        return {
            "response_pairs": [],
            "response_delay_distribution": [],
            "reply_matrix": {},
            "conversation_starters": [],
            "conversation_summary": {
                "total_conversations": 0,
                "overall_avg_conversation_length_messages": 0.0,
            },
        }

    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    df = df.dropna(subset=["Datetime"]).copy()
    if df.empty:
        return {
            "response_pairs": [],
            "response_delay_distribution": [],
            "reply_matrix": {},
            "conversation_starters": [],
            "conversation_summary": {
                "total_conversations": 0,
                "overall_avg_conversation_length_messages": 0.0,
            },
        }

    df = df.sort_values("Datetime").reset_index(drop=True)
    response_pairs, response_delay_distribution = _compute_response_pairs(df)
    reply_matrix = _compute_reply_matrix(df)
    conversation_starters, conversation_summary = _compute_conversation_starters(df)

    return {
        "response_pairs": response_pairs,
        "response_delay_distribution": response_delay_distribution,
        "reply_matrix": reply_matrix,
        "conversation_starters": conversation_starters,
        "conversation_summary": conversation_summary,
    }


def _compute_response_pairs(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pair_to_delays: dict[tuple[str, str], list[float]] = defaultdict(list)

    previous_person = None
    previous_time = None

    for row in df.itertuples(index=False):
        person = str(row.Person)
        current_time = row.Datetime
        if previous_person is not None and person != previous_person:
            delta_seconds = (current_time - previous_time).total_seconds()
            if delta_seconds >= 0:
                pair_to_delays[(previous_person, person)].append(delta_seconds)

        previous_person = person
        previous_time = current_time

    output: list[dict[str, Any]] = []
    distribution_output: list[dict[str, Any]] = []
    for (from_person, to_person), delays in sorted(pair_to_delays.items()):
        output.append(
            {
                "from": from_person,
                "to": to_person,
                "count": len(delays),
                "avg_response_minutes": round(mean(delays) / 60.0, 2),
            }
        )

        for delay_seconds in delays:
            distribution_output.append(
                {
                    "from": from_person,
                    "to": to_person,
                    "person": to_person,
                    "response_minutes": round(delay_seconds / 60.0, 2),
                }
            )

    return output, distribution_output


def _compute_reply_matrix(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    previous_person = None
    for row in df.itertuples(index=False):
        person = str(row.Person)
        if previous_person is not None and person != previous_person:
            transitions[previous_person][person] += 1
        previous_person = person

    return {
        sender: dict(sorted(recipients.items()))
        for sender, recipients in sorted(transitions.items())
    }


def _compute_conversation_starters(
    df: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gap_threshold = pd.Timedelta(hours=1)

    conversations: list[pd.DataFrame] = []
    current_start = 0
    for index in range(1, len(df)):
        gap = df.loc[index, "Datetime"] - df.loc[index - 1, "Datetime"]
        if gap > gap_threshold:
            conversations.append(df.iloc[current_start:index])
            current_start = index
    conversations.append(df.iloc[current_start:])

    starter_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "conversations_started": 0,
            "conversation_lengths": [],
            "first_response_minutes": [],
            "first_response_by": defaultdict(int),
        }
    )

    for conversation in conversations:
        if conversation.empty:
            continue

        starter = str(conversation.iloc[0]["Person"])
        starter_bucket = starter_stats[starter]
        starter_bucket["conversations_started"] += 1
        starter_bucket["conversation_lengths"].append(int(len(conversation)))

        first_message_time = conversation.iloc[0]["Datetime"]
        responder_row = None
        for row in conversation.iloc[1:].itertuples(index=False):
            if str(row.Person) != starter:
                responder_row = row
                break

        if responder_row is not None:
            responder = str(responder_row.Person)
            starter_bucket["first_response_by"][responder] += 1
            delay_minutes = (
                responder_row.Datetime - first_message_time
            ).total_seconds() / 60.0
            if delay_minutes >= 0:
                starter_bucket["first_response_minutes"].append(delay_minutes)

    starter_output: list[dict[str, Any]] = []
    for starter, stats in sorted(starter_stats.items()):
        avg_conversation_len = (
            round(mean(stats["conversation_lengths"]), 2)
            if stats["conversation_lengths"]
            else 0.0
        )
        avg_first_response = (
            round(mean(stats["first_response_minutes"]), 2)
            if stats["first_response_minutes"]
            else None
        )

        starter_output.append(
            {
                "person": starter,
                "conversations_started": int(stats["conversations_started"]),
                "avg_conversation_length_messages": avg_conversation_len,
                "avg_time_to_first_response_minutes": avg_first_response,
                "first_response_by": dict(sorted(stats["first_response_by"].items())),
            }
        )

    overall_avg = (
        round(
            mean(
                [
                    float(entry["avg_conversation_length_messages"])
                    for entry in starter_output
                    if entry["conversations_started"] > 0
                ]
            ),
            2,
        )
        if starter_output
        else 0.0
    )

    summary = {
        "total_conversations": int(
            sum(item["conversations_started"] for item in starter_output)
        ),
        "overall_avg_conversation_length_messages": overall_avg,
    }
    return starter_output, summary
