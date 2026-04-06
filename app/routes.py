import datetime
from pathlib import Path
import tempfile
import shutil

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
    send_file,
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
    list_recent_chats,
    load_chat_frames,
    query_messages,
    delete_chat,
)
from .graphs import generate_graphs


main_bp = Blueprint("main", __name__)

GRAPH_FILENAMES = [
    "kaajd-monthly-volume.png",
    "kaajd-day-hour-activity.png",
    "kaajd-message-length-distribution.png",
    "kaajd-top-emojis.png",
    "kaajd-response-heatmap.png",
    "kaajd-response-time-distribution.png",
    "kaajd-conversation-starters.png",
    "kaajd-affinity-heatmap.png",
    "kaajd-correlation-heatmap.png",
    "kaajd-media-links-per-person.png",
    "kaajd-media-monthly-trends.png",
    "kaajd-top-shared-domains.png",
    "wordcloud.png",
]


@main_bp.route("/", methods=["GET", "POST"])
@auth.login_required
def upload_file():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if not uploaded_file or not uploaded_file.filename:
            return _upload_error_response("Please select a .txt chat export file.")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}-{secure_filename(uploaded_file.filename)}"
        upload_dir = Path(current_app.config["UPLOAD_DIR"])
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / filename
        try:
            uploaded_file.save(file_path)

            analysis_result = analyze_chat(
                file_path=str(file_path),
                db_path=current_app.config.get("DATABASE_PATH"),
            )
            raw_data_df = analysis_result["raw_data_df"]
            if raw_data_df.empty:
                raise ValueError(
                    "No WhatsApp messages were detected in this file. "
                    "Please export the chat as a .txt file from WhatsApp (without media)."
                )

            generate_graphs(raw_data_df, analysis_result["output_dir"])
        except Exception as exc:
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass
            return _upload_error_response(_friendly_upload_error(exc))

        redirect_url = _build_dashboard_redirect_url(
            analysis_id=file_path.stem,
            chat_id=analysis_result.get("chat_id"),
            parser_format=analysis_result.get("parser_format", "unknown"),
            detected_language=analysis_result.get("detected_language", "unknown"),
            message_count=int(len(raw_data_df)),
        )
        if _is_ajax_request():
            return jsonify({"redirect_url": redirect_url})
        return redirect(redirect_url)

    error_message = request.args.get("error")
    return render_template("upload.html", error=error_message)


@main_bp.route("/demo")
@auth.login_required
def demo_analysis():
    sample_chat_path = Path(current_app.root_path).parent / "data" / "sample-chat.txt"
    demo_output_dir = Path(current_app.config["UPLOAD_DIR"]) / "sample-chat" / "output"
    if not sample_chat_path.exists():
        return redirect(
            url_for(
                "main.upload_file",
                error="Demo chat data is not available on this server.",
            )
        )

    try:
        analysis_result = analyze_chat(
            file_path=str(sample_chat_path),
            output_dir=str(demo_output_dir),
            db_path=current_app.config.get("DATABASE_PATH"),
        )
        generate_graphs(analysis_result["raw_data_df"], analysis_result["output_dir"])
    except Exception as exc:
        return redirect(url_for("main.upload_file", error=_friendly_upload_error(exc)))

    analysis_id = _extract_analysis_id(Path(analysis_result["output_dir"]))
    if not analysis_id:
        analysis_id = sample_chat_path.stem

    return redirect(
        _build_dashboard_redirect_url(
            analysis_id=analysis_id,
            chat_id=analysis_result.get("chat_id"),
            parser_format=analysis_result.get("parser_format", "unknown"),
            detected_language=analysis_result.get("detected_language", "unknown"),
            message_count=int(len(analysis_result["raw_data_df"])),
        )
    )


@main_bp.route("/results/<analysis_id>/export")
@auth.login_required
def export_results(analysis_id: str):
    output_dir = Path(current_app.config["UPLOAD_DIR"]) / analysis_id / "output"
    if not output_dir.exists() or not output_dir.is_dir():
        return jsonify({"error": "Results not found."}), 404

    # Create a temporary file to hold the zip archive
    temp_dir = Path(tempfile.gettempdir())
    zip_filename = f"kaajd-report-{analysis_id}.zip"
    zip_path = temp_dir / zip_filename

    # shutil.make_archive adds the .zip extension automatically
    base_name = str(temp_dir / f"kaajd-report-{analysis_id}")
    shutil.make_archive(base_name, "zip", root_dir=str(output_dir))

    return send_file(
        f"{base_name}.zip",
        as_attachment=True,
        download_name=zip_filename,
        mimetype="application/zip",
    )


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

    parse_feedback = None
    parser_format = request.args.get("parser_format")
    detected_language = request.args.get("detected_language")
    message_count = request.args.get("message_count", type=int)
    if parser_format or detected_language or message_count is not None:
        parse_feedback = {
            "parser_format": parser_format or "unknown",
            "detected_language": detected_language or "unknown",
            "message_count": message_count if message_count is not None else 0,
        }

    return render_template(
        "dashboard.html",
        analysis_id=analysis_id,
        chat_id=chat_id,
        table_html=table_html,
        graph_filenames=available_graphs,
        parse_feedback=parse_feedback,
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
        raw_data_df=filtered_df,
        response_patterns=response_patterns,
        media_links=media_links,
        topics=topics,
        relationships=relationships,
    )

    return jsonify(
        {
            "chat_id": chat_id,
            "context": context,
            "applied_filters": {
                "person": selected_person,
                "start_date": start_date,
                "end_date": end_date,
            },
            "plotly": plotly_payloads,
        }
    )


@main_bp.route("/api/chat/<int:chat_id>/delete", methods=["POST"])
@auth.login_required
def delete_chat_route(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if context is None:
        return jsonify({"error": "chat_not_found", "chat_id": chat_id}), 404

    output_dir_raw = context.get("chat", {}).get("output_dir", "")
    deleted_db = delete_chat(chat_id, db_path=current_app.config.get("DATABASE_PATH"))

    # Also remove output files from disk so they don't linger
    if output_dir_raw:
        output_dir = Path(output_dir_raw)
        if output_dir.exists() and output_dir.is_dir():
            try:
                shutil.rmtree(output_dir)
            except OSError:
                pass  # Best-effort; DB deletion already succeeded

    return jsonify({"success": deleted_db, "chat_id": chat_id})


@main_bp.route("/api/chats")
@auth.login_required
def chats_list():
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "invalid_limit"}), 400

    chats = list_recent_chats(
        limit=max(1, min(limit, 50)),
        db_path=current_app.config.get("DATABASE_PATH"),
    )

    response_rows = []
    for row in chats:
        output_dir_raw = str(row.get("output_dir") or "").strip()
        output_dir = Path(output_dir_raw) if output_dir_raw else None
        analysis_id = _extract_analysis_id(output_dir)
        response_rows.append(
            {
                "id": int(row["id"]),
                "source_name": row.get("source_name") or "unknown",
                "parser_format": row.get("parser_format") or "unknown",
                "detected_language": row.get("detected_language") or "unknown",
                "message_count": int(row.get("message_count") or 0),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "output_dir": output_dir_raw,
                "analysis_id": analysis_id,
                "static_files_missing": output_dir is None or not output_dir.exists(),
            }
        )

    return jsonify({"count": len(response_rows), "chats": response_rows})


def _parse_bool_query_param(value: str | None) -> bool | None:
    if value is None:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    return None


def _is_ajax_request() -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _upload_error_response(message: str):
    if _is_ajax_request():
        return jsonify({"error": message}), 400
    return render_template("upload.html", error=message), 400


def _friendly_upload_error(exc: Exception) -> str:
    detail = str(exc).strip().lower()
    if "whatsapp messages were detected" in detail:
        return str(exc)
    if "utf-8" in detail or "codec" in detail or "decode" in detail:
        return (
            "Could not read this file as UTF-8 text. "
            "Please export your chat from WhatsApp as a .txt file and try again."
        )
    return (
        "No WhatsApp messages were detected in this file. "
        "Make sure you export the chat as a .txt file from WhatsApp (without media)."
    )


def _build_dashboard_redirect_url(
    *,
    analysis_id: str,
    chat_id: int | None,
    parser_format: str,
    detected_language: str,
    message_count: int,
) -> str:
    return url_for(
        "main.dashboard",
        analysis_id=analysis_id,
        chat_id=chat_id,
        parser_format=parser_format,
        detected_language=detected_language,
        message_count=message_count,
    )


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


def _extract_analysis_id(output_dir: Path | None) -> str | None:
    if output_dir is None:
        return None

    try:
        output_parts = output_dir.resolve().parts
    except OSError:
        output_parts = output_dir.parts

    if not output_parts:
        return None

    if output_parts[-1] == "output" and len(output_parts) >= 2:
        return output_parts[-2]
    return output_dir.name or None
