from datetime import timedelta
from pathlib import Path
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from wordcloud import WordCloud
import plotly.graph_objects as go

from .analyzers import (
    analyze_response_patterns,
    analyze_media_links,
    analyze_topics,
    analyze_relationships,
)
from .charts_payloads import build_plotly_payloads


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

    generated_files.append(_plot_wordcloud(df, output_path))

    # Plotly static graphs
    try:
        response_patterns = analyze_response_patterns(raw_data_df)
        media_links = analyze_media_links(raw_data_df)
        topics = analyze_topics(raw_data_df)
        relationships = analyze_relationships(raw_data_df)
        payloads = build_plotly_payloads(
            raw_data_df=raw_data_df,
            response_patterns=response_patterns,
            media_links=media_links,
            topics=topics,
            relationships=relationships,
        )

        static_files = _generate_plotly_static_graphs(payloads, output_path)
        generated_files.extend(static_files)
    except Exception as e:
        print(f"Warning: Failed to generate static Plotly graphs: {e}")

    return generated_files


def _generate_plotly_static_graphs(payloads: dict, output_dir: Path) -> list[str]:
    generated = []
    act = payloads.get("activity", {})
    res = payloads.get("response_patterns", {})
    med = payloads.get("media_links", {})

    layout_opts = dict(width=1000, height=600, margin=dict(t=52, l=46, r=16, b=52))

    # Activity: Monthly Volume
    if act.get("monthly_volume", {}).get("x"):
        fig = go.Figure(
            data=[
                go.Bar(
                    x=act["monthly_volume"]["x"],
                    y=act["monthly_volume"]["y"],
                    marker_color="#2e6f95",
                )
            ]
        )
        fig.update_layout(title="Message Volume Over Time", **layout_opts)
        f = "kaajd-monthly-volume.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Activity: Day x Hour
    if act.get("day_hour_heatmap", {}).get("z"):
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=act["day_hour_heatmap"]["x"],
                    y=act["day_hour_heatmap"]["y"],
                    z=act["day_hour_heatmap"]["z"],
                    colorscale="YlGnBu",
                )
            ]
        )
        fig.update_layout(
            title="Day x Hour Activity Heatmap",
            xaxis_title="Hour of day",
            yaxis_title="Day of week",
            **layout_opts,
        )
        f = "kaajd-day-hour-activity.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Activity: Message Length Distribution
    if act.get("message_length"):
        traces = [
            go.Box(name=t["name"], y=t["y"], boxmean="sd", boxpoints=False)
            for t in act["message_length"]
        ]
        fig = go.Figure(data=traces)
        fig.update_layout(
            title="Message Length Distribution (characters)",
            yaxis_title="Characters",
            **layout_opts,
        )
        f = "kaajd-message-length-distribution.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Activity: Top Emojis
    if act.get("emojis_overall", {}).get("x"):
        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(reversed(act["emojis_overall"]["y"])),
                    y=list(reversed(act["emojis_overall"]["x"])),
                    orientation="h",
                    marker_color="#eeb422",
                )
            ]
        )
        fig.update_layout(
            title="Top 10 Emojis Overall",
            xaxis_title="Frequency",
            yaxis_title="Emoji",
            **layout_opts,
        )
        f = "kaajd-top-emojis.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Response: Heatmap
    if res.get("response_time_heatmap", {}).get("z"):
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=res["response_time_heatmap"]["x"],
                    y=res["response_time_heatmap"]["y"],
                    z=res["response_time_heatmap"]["z"],
                    colorscale="Viridis",
                    zmin=0,
                    xgap=1,
                    ygap=1,
                )
            ]
        )
        fig.update_layout(
            title="Average Response Time (minutes)",
            xaxis_title="Replied to (Sender)",
            yaxis_title="Replier (Responder)",
            margin=dict(l=200, t=52, r=16, b=52),
            width=1000,
            height=600,
        )
        f = "kaajd-response-heatmap.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Media: Per-person stacked bar
    if med.get("per_person_stacked", {}).get("x"):
        ps = med["per_person_stacked"]
        fig = go.Figure(
            data=[
                go.Bar(name="Media", x=ps["x"], y=ps["media"]),
                go.Bar(name="Links", x=ps["x"], y=ps["links"]),
            ]
        )
        fig.update_layout(
            title="Media/Link Messages per Person",
            barmode="stack",
            yaxis_title="Number of messages",
            **layout_opts,
        )
        f = "kaajd-media-links-per-person.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Media: Monthly trends
    if med.get("monthly_traces"):
        traces = [
            go.Scatter(
                name=t["name"], x=t["x"], y=t["y"], mode="lines", stackgroup="one"
            )
            for t in med["monthly_traces"]
        ]
        fig = go.Figure(data=traces)
        fig.update_layout(
            title="Monthly Media/Link Trends (Group Total)", **layout_opts
        )
        f = "kaajd-media-monthly-trends.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Media: Top domains
    if med.get("top_domains_bar", {}).get("x"):
        td = med["top_domains_bar"]
        fig = go.Figure(data=[go.Bar(x=td["x"], y=td["y"], marker_color="#1f8a70")])
        fig.update_layout(
            title="Top Shared Domains",
            yaxis_title="Number of links",
            **layout_opts,
        )
        f = "kaajd-top-shared-domains.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Response: Distribution (box plot per person, capped at 4h)
    if res.get("response_time_distribution", {}).get("traces"):
        traces = [
            go.Box(name=t["name"], y=t["y"], boxmean="sd", boxpoints=False)
            for t in res["response_time_distribution"]["traces"]
        ]
        fig = go.Figure(data=traces)
        fig.update_layout(
            title="Response Time Distribution (minutes, capped at 4h)",
            yaxis_title="Response time (minutes)",
            **layout_opts,
        )
        f = "kaajd-response-time-distribution.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Response: Conversation starters
    if res.get("conversation_starters_bar", {}).get("x"):
        cs = res["conversation_starters_bar"]
        fig = go.Figure(data=[go.Bar(x=cs["x"], y=cs["y"], marker_color="#2e6f95")])
        fig.update_layout(
            title="Conversations Started",
            yaxis_title="Conversations started",
            **layout_opts,
        )
        f = "kaajd-conversation-starters.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Relationships: Affinity heatmap
    rel = payloads.get("relationships", {})
    if rel.get("affinity_heatmap", {}).get("z"):
        ah = rel["affinity_heatmap"]
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=ah["x"],
                    y=ah["y"],
                    z=ah["z"],
                    colorscale=[[0, "white"], [1, "rgb(8,48,107)"]],
                )
            ]
        )
        fig.update_layout(
            title="Affinity Scores",
            xaxis_title="Replied to →",
            yaxis_title="Replier ↓",
            margin=dict(l=200, t=52, r=16, b=52),
            width=1000,
            height=600,
        )
        f = "kaajd-affinity-heatmap.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    # Relationships: Correlation heatmap
    if rel.get("correlation_heatmap", {}).get("z"):
        ch = rel["correlation_heatmap"]
        fig = go.Figure(
            data=[
                go.Heatmap(
                    x=ch["x"],
                    y=ch["y"],
                    z=ch["z"],
                    colorscale="RdBu",
                    zmid=0,
                )
            ]
        )
        fig.update_layout(
            title="Daily Activity Correlation",
            xaxis_title="Participant",
            yaxis_title="Participant",
            margin=dict(l=200, t=52, r=16, b=52),
            width=1000,
            height=600,
        )
        f = "kaajd-correlation-heatmap.png"
        fig.write_image(str(output_dir / f))
        generated.append(f)

    return generated


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
        "echt",
        "net",
        "gewoon",
        "misschien",
        "jullie",
        "ook",
        "nog",
        "dit",
        "die",
        "dat",
        "een",
        "wat",
        "hoe",
        "als",
        "dan",
        "maar",
        "meer",
        "had",
        "heeft",
        "heb",
        "hem",
        "zijn",
        "deze",
        "kunnen",
        "moeten",
        "weten",
        "zeker",
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
