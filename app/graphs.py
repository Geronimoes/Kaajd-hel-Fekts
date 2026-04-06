from datetime import timedelta
from pathlib import Path
import re

import emoji
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from textblob import TextBlob
from wordcloud import WordCloud


def generate_graphs(raw_data_df: pd.DataFrame, output_dir: str | Path) -> list[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if raw_data_df.empty:
        return []

    df = raw_data_df.copy()
    if "IsSystemMessage" in df.columns:
        df = df[~df["IsSystemMessage"]]

    if df.empty:
        return []

    df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")
    df["Time"] = pd.to_datetime(df["Time"], format="%H:%M").dt.time

    generated_files = []

    generated_files.append(_plot_messages_over_time(df, output_path))
    generated_files.append(_plot_most_active_times(df, output_path))
    generated_files.append(_plot_conversation_starters(df, output_path))
    generated_files.append(_plot_message_length_distribution(df, output_path))
    generated_files.append(_plot_wordcloud(df, output_path))
    generated_files.append(_plot_top_emojis(df, output_path))
    generated_files.append(_plot_sentiment(df, output_path))

    return generated_files


def _plot_messages_over_time(df: pd.DataFrame, output_dir: Path) -> str:
    date_counts = df["Date"].value_counts().sort_index().reset_index()
    date_counts.columns = ["Date", "Count"]
    date_counts["Days"] = (date_counts["Date"] - date_counts["Date"][0]).dt.days

    plt.figure(figsize=(10, 6))
    plt.scatter(date_counts["Date"], date_counts["Count"], s=5, color="blue")
    lowess = sm.nonparametric.lowess(
        date_counts["Count"], date_counts["Days"], frac=0.1
    )
    plt.plot(date_counts["Date"], lowess[:, 1], color="red")
    plt.title("Message Frequency Over Time")
    plt.xlabel("Date")
    plt.ylabel("Number of Messages")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    filename = "messages_over_time.png"
    plt.savefig(output_dir / filename)
    plt.close()
    return filename


def _plot_most_active_times(df: pd.DataFrame, output_dir: Path) -> str:
    activity_df = df.copy()
    activity_df["Hour"] = activity_df["Time"].apply(lambda value: value.hour)
    activity_df["Quarter"] = activity_df["Date"].dt.quarter

    activity_df.groupby(["Hour", "Quarter"]).size().unstack().plot(kind="line")
    plt.title("Most Active Times")
    plt.xlabel("Hour of the Day")
    plt.ylabel("Number of Messages")

    filename = "most_active_times.png"
    plt.savefig(output_dir / filename)
    plt.close()
    return filename


def _plot_conversation_starters(df: pd.DataFrame, output_dir: Path) -> str:
    starters_df = df.copy()
    starters_df["Datetime"] = pd.to_datetime(
        starters_df["Date"].astype(str) + " " + starters_df["Time"].astype(str)
    )
    starters_df["Time_Diff"] = starters_df["Datetime"].diff()
    starters_df["Conversation_Starter"] = starters_df["Time_Diff"] > timedelta(hours=1)
    conversation_starters = starters_df[starters_df["Conversation_Starter"]][
        "Person"
    ].value_counts()

    conversation_starters.plot(kind="bar")
    plt.title("Conversation Starters")
    plt.xlabel("Person")
    plt.ylabel("Number of Conversations Started")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    filename = "conversation_starters.png"
    plt.savefig(output_dir / filename)
    plt.close()
    return filename


def _plot_message_length_distribution(df: pd.DataFrame, output_dir: Path) -> str:
    message_length_df = df.copy()
    message_length_df["Message_Length"] = message_length_df["Message"].apply(len)
    cutoff_length = np.percentile(message_length_df["Message_Length"], 95)

    plt.figure(figsize=(10, 6))
    message_length_df["Message_Length"].plot(
        kind="hist", bins=30, range=(0, cutoff_length)
    )
    plt.title("Message Length Distribution")
    plt.xlabel("Message Length")
    plt.ylabel("Frequency")

    filename = "message_length_distribution.png"
    plt.savefig(output_dir / filename)
    plt.close()
    return filename


def _plot_wordcloud(df: pd.DataFrame, output_dir: Path) -> str:
    text = " ".join(df["Message"])
    from nltk.corpus import stopwords

    try:
        dutch_stops = set(stopwords.words("dutch"))
    except LookupError:
        dutch_stops = set()

    custom_stops = {
        "Media",
        "weggelaten",
        "youtu.be",
        "youtu",
        "watch",
        "alleen",
        "html",
        "denk",
        "V",
        "be",
        "http",
        "https",
        "we",
        "gaan",
        "zeg",
        "zegt",
        "zeggen",
        "wel",
        "even",
        "gaat",
        "weer",
        "zien",
        "komt",
        "kom",
        "komen",
        "zal",
        "mee",
        "www",
        "nl",
        "com",
        "youtube",
        "goed",
    }
    custom_stops.update(dutch_stops)

    wordcloud = WordCloud(stopwords=custom_stops, width=800, height=400).generate(text)
    plt.figure(figsize=(15, 7))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")

    filename = "wordcloud.png"
    plt.savefig(output_dir / filename)
    plt.close()
    return filename


def _extract_emojis(value: str) -> list[str]:
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f700-\U0001f77f"
        "\U0001f780-\U0001f7ff"
        "\U0001f800-\U0001f8ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001fa6f"
        "\U0001fa70-\U0001faff"
        "\U00002702-\U000027b0"
        "\U000024c2-\U0001f251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.findall(value)


def _plot_top_emojis(df: pd.DataFrame, output_dir: Path) -> str:
    emoji_df = df.copy()
    emoji_df["Emojis"] = emoji_df["Message"].apply(_extract_emojis)
    all_emojis = sum(emoji_df["Emojis"], [])

    if all_emojis:
        emoji_counts = pd.Series(all_emojis).value_counts().head(10)
        emoji_counts.index = [
            emoji.demojize(char).replace(":", "").replace("_", " ")
            for char in emoji_counts.index
        ]
        emoji_counts.plot(kind="bar", figsize=(10, 6))
    else:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "No emoji found", ha="center", va="center")
        plt.xlim(0, 1)
        plt.ylim(0, 1)

    plt.title("Top 10 Emojis")
    plt.ylabel("Frequency")
    plt.xticks(rotation=45, ha="right")

    filename = "top_emojis.png"
    plt.savefig(output_dir / filename, bbox_inches="tight")
    plt.close()
    return filename


def _plot_sentiment(df: pd.DataFrame, output_dir: Path) -> str:
    sentiment_df = df.copy()
    sentiment_df["Polarity"] = sentiment_df["Message"].apply(
        lambda message: TextBlob(message).sentiment.polarity
    )
    sentiment_df["Polarity_Rolling"] = (
        sentiment_df["Polarity"].rolling(window=500, center=True).mean()
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(sentiment_df.index, sentiment_df["Polarity"], label="Polarity", alpha=0.5)
    ax.plot(
        sentiment_df.index,
        sentiment_df["Polarity_Rolling"],
        label="Trend",
        color="red",
        linewidth=2,
    )
    ax.set_title("Sentiment Over Time")
    ax.set_xlabel("Message index")
    ax.set_ylabel("Sentiment Polarity")
    ax.legend()
    ax.grid(True)
    ax.annotate("Positive", xy=(0.1, 0.9), xycoords="axes fraction", color="green")
    ax.annotate("Negative", xy=(0.1, 0.1), xycoords="axes fraction", color="red")

    filename = "sentiment.png"
    plt.savefig(output_dir / filename, bbox_inches="tight")
    plt.close()
    return filename
