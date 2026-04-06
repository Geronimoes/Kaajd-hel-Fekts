from __future__ import annotations

import re
from typing import Any

import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


_DUTCH_STOPWORDS = {
    "aan",
    "af",
    "al",
    "als",
    "bij",
    "dat",
    "de",
    "den",
    "der",
    "des",
    "die",
    "dit",
    "een",
    "en",
    "er",
    "het",
    "hier",
    "hij",
    "hoe",
    "hun",
    "ik",
    "in",
    "is",
    "je",
    "kan",
    "me",
    "men",
    "met",
    "mij",
    "nog",
    "nu",
    "of",
    "ons",
    "ook",
    "te",
    "toch",
    "toen",
    "tot",
    "u",
    "uit",
    "uw",
    "van",
    "veel",
    "voor",
    "want",
    "was",
    "wat",
    "we",
    "wel",
    "wie",
    "wij",
    "zal",
    "ze",
    "zei",
    "zelf",
    "zich",
    "zij",
    "zijn",
    "zo",
    "zonder",
    "zou",
}

_CUSTOM_STOPWORDS = {
    "http",
    "https",
    "www",
    "com",
    "nl",
    "media",
    "omitted",
    "weggelaten",
}


def analyze_topics(
    raw_data_df: pd.DataFrame,
    *,
    max_topics: int = 5,
    terms_per_topic: int = 8,
    trend_terms: int = 8,
) -> dict[str, Any]:
    if raw_data_df.empty:
        return _empty_topics_result()

    df = raw_data_df.copy()
    if "IsSystemMessage" in df.columns:
        df = df[~df["IsSystemMessage"]]
    if df.empty:
        return _empty_topics_result()

    df["Message"] = df["Message"].fillna("").astype(str)
    df = df[df["Message"].str.strip() != ""]
    if df.empty:
        return _empty_topics_result()

    df["Datetime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    df = df.dropna(subset=["Datetime"])
    if df.empty:
        return _empty_topics_result()

    df["Month"] = df["Datetime"].dt.to_period("M").astype(str)
    monthly_docs_df = (
        df.groupby("Month")["Message"]
        .apply(lambda values: " ".join(values))
        .reset_index()
    )
    monthly_docs_df["CleanText"] = monthly_docs_df["Message"].apply(_normalize_text)
    monthly_docs_df = monthly_docs_df[monthly_docs_df["CleanText"].str.strip() != ""]
    if monthly_docs_df.empty:
        return _empty_topics_result()

    stopwords = set(ENGLISH_STOP_WORDS)
    stopwords.update(_DUTCH_STOPWORDS)
    stopwords.update(_CUSTOM_STOPWORDS)

    vectorizer = TfidfVectorizer(
        stop_words=sorted(stopwords),
        max_features=4000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b",
        ngram_range=(1, 2),
    )

    matrix = vectorizer.fit_transform(monthly_docs_df["CleanText"])
    if matrix.shape[1] == 0:
        return _empty_topics_result()

    feature_names = vectorizer.get_feature_names_out()
    monthly_trends = _extract_monthly_trends(
        matrix=matrix,
        feature_names=feature_names,
        months=monthly_docs_df["Month"].tolist(),
        top_k=trend_terms,
    )

    n_docs = matrix.shape[0]
    n_features = matrix.shape[1]
    topic_count = max(2, min(max_topics, n_docs, n_features))

    topic_model = NMF(
        n_components=topic_count, random_state=42, init="nndsvda", max_iter=400
    )
    doc_topic = topic_model.fit_transform(matrix)
    topic_term = topic_model.components_

    topics = _extract_topics(
        topic_term=topic_term,
        doc_topic=doc_topic,
        feature_names=feature_names,
        months=monthly_docs_df["Month"].tolist(),
        terms_per_topic=terms_per_topic,
    )

    return {
        "monthly_trends": monthly_trends,
        "topics": topics,
        "meta": {
            "months_analyzed": int(n_docs),
            "features": int(n_features),
            "topic_count": int(topic_count),
            "vectorizer": "tfidf",
            "model": "nmf",
        },
    }


def _extract_monthly_trends(
    *, matrix, feature_names: list[str] | Any, months: list[str], top_k: int
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    dense = matrix.toarray()
    for idx, month in enumerate(months):
        row = dense[idx]
        if row.size == 0:
            output.append({"month": month, "top_terms": []})
            continue

        top_indices = row.argsort()[::-1][:top_k]
        top_terms = [
            {"term": str(feature_names[i]), "score": round(float(row[i]), 5)}
            for i in top_indices
            if row[i] > 0
        ]
        output.append({"month": month, "top_terms": top_terms})
    return output


def _extract_topics(
    *,
    topic_term,
    doc_topic,
    feature_names,
    months: list[str],
    terms_per_topic: int,
) -> list[dict[str, Any]]:
    topics_output: list[dict[str, Any]] = []

    for topic_idx, weights in enumerate(topic_term):
        top_term_indices = weights.argsort()[::-1][:terms_per_topic]
        top_terms = [
            {"term": str(feature_names[i]), "weight": round(float(weights[i]), 5)}
            for i in top_term_indices
            if weights[i] > 0
        ]

        month_weights = doc_topic[:, topic_idx]
        ranked_month_indices = month_weights.argsort()[::-1][:5]
        top_months = [
            {
                "month": months[i],
                "weight": round(float(month_weights[i]), 5),
            }
            for i in ranked_month_indices
            if month_weights[i] > 0
        ]

        topics_output.append(
            {
                "topic_id": int(topic_idx + 1),
                "top_terms": top_terms,
                "top_months": top_months,
            }
        )

    return topics_output


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"https?://\S+", " ", lowered)
    lowered = re.sub(r"www\.\S+", " ", lowered)
    lowered = re.sub(r"[^a-z0-9_\-\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _empty_topics_result() -> dict[str, Any]:
    return {
        "monthly_trends": [],
        "topics": [],
        "meta": {
            "months_analyzed": 0,
            "features": 0,
            "topic_count": 0,
            "vectorizer": "tfidf",
            "model": "nmf",
        },
    }
