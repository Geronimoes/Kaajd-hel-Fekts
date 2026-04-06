from __future__ import annotations

from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

import pandas as pd


def analyze_media_links(raw_data_df: pd.DataFrame) -> dict[str, Any]:
    if raw_data_df.empty:
        return {
            "per_person": [],
            "by_month": [],
            "top_domains": [],
        }

    df = raw_data_df.copy()
    if "IsSystemMessage" in df.columns:
        df = df[~df["IsSystemMessage"]]
    if df.empty:
        return {
            "per_person": [],
            "by_month": [],
            "top_domains": [],
        }

    df["Person"] = df["Person"].fillna("").astype(str)
    df = df[df["Person"].str.strip() != ""]
    if df.empty:
        return {
            "per_person": [],
            "by_month": [],
            "top_domains": [],
        }

    if "HasLink" not in df.columns:
        df["HasLink"] = False
    if "IsMediaMessage" not in df.columns:
        df["IsMediaMessage"] = False

    df["HasLink"] = df["HasLink"].astype(bool)
    df["IsMediaMessage"] = df["IsMediaMessage"].astype(bool)

    per_person = _per_person_stats(df)
    by_month = _monthly_breakdown(df)
    top_domains = _top_domains(df)

    return {
        "per_person": per_person,
        "by_month": by_month,
        "top_domains": top_domains,
    }


def _per_person_stats(df: pd.DataFrame) -> list[dict[str, Any]]:
    total_counts = df.groupby("Person").size().to_dict()
    link_counts = df[df["HasLink"]].groupby("Person").size().to_dict()
    media_counts = df[df["IsMediaMessage"]].groupby("Person").size().to_dict()

    output: list[dict[str, Any]] = []
    for person in sorted(total_counts.keys()):
        total = int(total_counts.get(person, 0))
        links = int(link_counts.get(person, 0))
        media = int(media_counts.get(person, 0))
        text_messages = max(total - media, 0)
        media_to_text_ratio = round(media / text_messages, 3) if text_messages else None

        output.append(
            {
                "person": person,
                "total_messages": total,
                "link_messages": links,
                "media_messages": media,
                "text_messages": text_messages,
                "media_to_text_ratio": media_to_text_ratio,
            }
        )

    return sorted(output, key=lambda row: row["total_messages"], reverse=True)


def _monthly_breakdown(df: pd.DataFrame) -> list[dict[str, Any]]:
    df = df.copy()
    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    df = df.dropna(subset=["Datetime"])
    if df.empty:
        return []

    df["Month"] = df["Datetime"].dt.to_period("M").astype(str)
    grouped = (
        df.groupby(["Month", "Person"])
        .agg(
            total_messages=("Message", "size"),
            link_messages=("HasLink", "sum"),
            media_messages=("IsMediaMessage", "sum"),
        )
        .reset_index()
    )

    rows = grouped.to_dict(orient="records")
    for row in rows:
        row["total_messages"] = int(row["total_messages"])
        row["link_messages"] = int(row["link_messages"])
        row["media_messages"] = int(row["media_messages"])
    return rows


def _top_domains(df: pd.DataFrame, top_n: int = 20) -> list[dict[str, Any]]:
    domain_counts: dict[str, int] = defaultdict(int)
    domain_by_person: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    link_df = df[df["HasLink"]]
    for row in link_df.itertuples(index=False):
        person = str(row.Person)
        message = str(row.Message)
        for domain in _extract_domains(message):
            domain_counts[domain] += 1
            domain_by_person[domain][person] += 1

    output = []
    for domain, count in sorted(
        domain_counts.items(), key=lambda item: item[1], reverse=True
    )[:top_n]:
        output.append(
            {
                "domain": domain,
                "count": int(count),
                "by_person": dict(sorted(domain_by_person[domain].items())),
            }
        )
    return output


def _extract_domains(message: str) -> list[str]:
    DOMAIN_ALIASES = {
        "youtu.be": "youtube.com",
        "m.youtube.com": "youtube.com",
        "mobile.twitter.com": "twitter.com",
        "m.facebook.com": "facebook.com",
    }
    tokens = message.replace("\n", " ").split()
    domains: list[str] = []
    for token in tokens:
        lowered = token.strip("()[]<>{},.!?\"'").lower()
        if lowered.startswith("www."):
            lowered = f"https://{lowered}"
        if not lowered.startswith("http://") and not lowered.startswith("https://"):
            continue

        parsed = urlparse(lowered)
        host = parsed.netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        if host:
            host = DOMAIN_ALIASES.get(host, host)
            domains.append(host)
    return domains
