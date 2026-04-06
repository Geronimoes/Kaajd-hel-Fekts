import datetime
from pathlib import Path

from bs4 import BeautifulSoup
import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from .analyzers import (
    analyze_media_links,
    analyze_relationships,
    analyze_response_patterns,
    analyze_topics,
)
from .analyzer import analyze_chat
from .auth import auth
from .charts_payloads import build_plotly_payloads
from .database import (
    get_chat_by_output_dir,
    get_chat_context,
    load_chat_frames,
    query_messages,
)
from .graphs import generate_graphs


main_bp = Blueprint("main", __name__)

GRAPH_FILENAMES = [
    "conversation_starters.png",
    "message_length_distribution.png",
    "messages_over_time.png",
    "most_active_times.png",
    "sentiment.png",
    "top_emojis.png",
    "wordcloud.png",
]


@main_bp.route("/", methods=["GET", "POST"])
@auth.login_required
def upload_file():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename:
            return render_template(
                "upload.html", error="Please select a .txt chat export file."
            )

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}-{secure_filename(uploaded_file.filename)}"
        upload_dir = Path(current_app.config["UPLOAD_DIR"])
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        uploaded_file.save(file_path)

        analysis_result = analyze_chat(
            file_path=str(file_path), db_path=current_app.config.get("DATABASE_PATH")
        )
        generate_graphs(analysis_result["raw_data_df"], analysis_result["output_dir"])

        analysis_id = file_path.stem
        return redirect(
            url_for(
                "main.dashboard",
                analysis_id=analysis_id,
                chat_id=analysis_result.get("chat_id"),
            )
        )

    return render_template("upload.html")


@main_bp.route("/results/<analysis_id>")
@auth.login_required
def dashboard(analysis_id: str):
    output_dir = Path(current_app.config["UPLOAD_DIR"]) / analysis_id / "output"
    summary_file = output_dir / "summary.html"
    if not summary_file.exists():
        return redirect(url_for("main.upload_file"))

    chat_id = request.args.get("chat_id", type=int)
    if chat_id is None:
        chat_row = get_chat_by_output_dir(
            output_dir, db_path=current_app.config.get("DATABASE_PATH")
        )
        if chat_row is not None:
            chat_id = int(chat_row["id"])

    with summary_file.open("r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
        table_html = str(soup.find("table"))

    available_graphs = [
        image for image in GRAPH_FILENAMES if (output_dir / image).exists()
    ]

    return render_template(
        "dashboard.html",
        analysis_id=analysis_id,
        chat_id=chat_id,
        table_html=table_html,
        graph_filenames=available_graphs,
    )


@main_bp.route("/api/chat/<int:chat_id>/context")
@auth.login_required
def chat_context(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404
    return jsonify(context)


@main_bp.route("/api/chat/<int:chat_id>/messages")
@auth.login_required
def chat_messages(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    person = request.args.get("person")
    has_link = _parse_bool_query_param(request.args.get("has_link"))
    is_media_message = _parse_bool_query_param(request.args.get("is_media_message"))

    try:
        limit = int(request.args.get("limit", 200))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return (
            jsonify(
                {
                    "error": "invalid_pagination",
                    "detail": "limit and offset must be integers",
                }
            ),
            400,
        )

    messages = query_messages(
        chat_id,
        person=person,
        has_link=has_link,
        is_media_message=is_media_message,
        limit=limit,
        offset=offset,
        db_path=current_app.config.get("DATABASE_PATH"),
    )
    return jsonify(
        {
            "chat_id": chat_id,
            "count": len(messages),
            "filters": {
                "person": person,
                "has_link": has_link,
                "is_media_message": is_media_message,
                "limit": max(1, limit),
                "offset": max(0, offset),
            },
            "messages": messages,
        }
    )


@main_bp.route("/api/chat/<int:chat_id>/response-patterns")
@auth.login_required
def chat_response_patterns(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    raw_data_df, _ = load_chat_frames(
        chat_id, db_path=current_app.config.get("DATABASE_PATH")
    )
    analysis = analyze_response_patterns(raw_data_df)
    return jsonify({"chat_id": chat_id, **analysis})


@main_bp.route("/api/chat/<int:chat_id>/media-links")
@auth.login_required
def chat_media_links(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    raw_data_df, _ = load_chat_frames(
        chat_id, db_path=current_app.config.get("DATABASE_PATH")
    )
    analysis = analyze_media_links(raw_data_df)
    return jsonify({"chat_id": chat_id, **analysis})


@main_bp.route("/api/chat/<int:chat_id>/topics")
@auth.login_required
def chat_topics(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    raw_data_df, _ = load_chat_frames(
        chat_id, db_path=current_app.config.get("DATABASE_PATH")
    )

    try:
        max_topics = int(request.args.get("max_topics", 5))
    except ValueError:
        return jsonify({"error": "invalid_max_topics"}), 400

    analysis = analyze_topics(raw_data_df, max_topics=max(2, min(max_topics, 10)))
    return jsonify({"chat_id": chat_id, **analysis})


@main_bp.route("/api/chat/<int:chat_id>/relationships")
@auth.login_required
def chat_relationships(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    raw_data_df, _ = load_chat_frames(
        chat_id, db_path=current_app.config.get("DATABASE_PATH")
    )
    analysis = analyze_relationships(raw_data_df)
    return jsonify({"chat_id": chat_id, **analysis})


@main_bp.route("/api/chat/<int:chat_id>/dashboard-data")
@auth.login_required
def chat_dashboard_data(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    raw_data_df, _ = load_chat_frames(
        chat_id, db_path=current_app.config.get("DATABASE_PATH")
    )

    selected_person = request.args.get("person")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    try:
        filtered_df = _filter_raw_data_df(
            raw_data_df,
            person=selected_person,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError:
        return jsonify({"error": "invalid_date_filter"}), 400

    response_patterns = analyze_response_patterns(filtered_df)
    media_links = analyze_media_links(filtered_df)
    topics = analyze_topics(filtered_df)
    relationships = analyze_relationships(filtered_df)
    plotly_payloads = build_plotly_payloads(
        response_patterns=response_patterns,
        media_links=media_links,
        topics=topics,
        relationships=relationships,
    )

    return jsonify(
        {
            "chat_id": chat_id,
            "context": context,
            "analysis": {
                "response_patterns": response_patterns,
                "media_links": media_links,
                "topics": topics,
                "relationships": relationships,
            },
            "applied_filters": {
                "person": selected_person,
                "start_date": start_date,
                "end_date": end_date,
            },
            "plotly": plotly_payloads,
        }
    )


def _parse_bool_query_param(value: str | None) -> bool | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def _filter_raw_data_df(
    raw_data_df: pd.DataFrame,
    *,
    person: str | None,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    filtered = raw_data_df.copy()
    if person and person != "all":
        filtered = filtered[filtered["Person"].astype(str) == person]

    if not start_date and not end_date:
        return filtered

    filtered["DateObj"] = pd.to_datetime(
        filtered["Date"].astype(str), format="%d-%m-%Y", errors="coerce"
    )
    filtered = filtered.dropna(subset=["DateObj"])

    if start_date:
        start = pd.to_datetime(start_date, format="%Y-%m-%d", errors="raise")
        filtered = filtered[filtered["DateObj"] >= start]
    if end_date:
        end = pd.to_datetime(end_date, format="%Y-%m-%d", errors="raise")
        filtered = filtered[filtered["DateObj"] <= end]

    return filtered.drop(columns=["DateObj"], errors="ignore")
