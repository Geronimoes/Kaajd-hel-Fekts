from collections import defaultdict
from pathlib import Path

import pandas as pd

from .database import (
    build_source_hash,
    get_chat_by_source_hash,
    load_chat_frames,
    store_analysis_result,
)
from .parser import parse_chat


def build_chat_stats(raw_data_df: pd.DataFrame) -> pd.DataFrame:
    stats_source_df = raw_data_df.copy()
    if "IsSystemMessage" in stats_source_df.columns:
        stats_source_df = stats_source_df[~stats_source_df["IsSystemMessage"]]

    message_count: defaultdict[str, int] = defaultdict(int)
    total_char_count_per_person: defaultdict[str, int] = defaultdict(int)
    total_char_count_all = 0

    for row in stats_source_df.itertuples(index=False):
        message_count[row.Person] += 1
        message_length = len(row.Message)
        total_char_count_per_person[row.Person] += message_length
        total_char_count_all += message_length

    chat_stats_df = pd.DataFrame(
        {
            "Person": list(message_count.keys()),
            "Total Messages": list(message_count.values()),
            "Average Message Length (chars)": [
                round(total_char_count_per_person[person] / message_count[person], 2)
                for person in message_count
            ],
            "Total Characters": list(total_char_count_per_person.values()),
        }
    )

    total_messages = sum(message_count.values())
    overall_average = (
        round(total_char_count_all / total_messages, 2) if total_messages else 0.0
    )
    total_row = pd.DataFrame(
        [
            {
                "Person": "Total (All Persons)",
                "Total Messages": total_messages,
                "Average Message Length (chars)": overall_average,
                "Total Characters": total_char_count_all,
            }
        ]
    )

    return pd.concat([chat_stats_df, total_row], ignore_index=True)


def analyze_chat(
    file_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    persist: bool = True,
    reuse_cached: bool = True,
    db_path: str | Path | None = None,
) -> dict:
    source_path = Path(file_path).resolve()

    if persist and reuse_cached:
        source_hash = build_source_hash(source_path)
        cached_chat = get_chat_by_source_hash(source_hash, db_path=db_path)
        if cached_chat is not None:
            cached_chat_id = int(cached_chat["id"])
            raw_data_df, chat_stats_df = load_chat_frames(
                cached_chat_id, db_path=db_path
            )

            if output_dir is not None:
                resolved_output_path = Path(output_dir)
            else:
                # Always resolve based on the current requested file_path so we don't dump to an old path
                resolved_output_path = source_path.parent / source_path.stem / "output"

            resolved_output_path.mkdir(parents=True, exist_ok=True)
            raw_data_csv_path, html_path, json_path, chat_stats_json = (
                _write_analysis_outputs(
                    raw_data_df=raw_data_df,
                    chat_stats_df=chat_stats_df,
                    output_path=resolved_output_path,
                )
            )

            return {
                "raw_data_df": raw_data_df,
                "output_dir": str(resolved_output_path),
                "raw_data_csv_path": str(raw_data_csv_path),
                "parser_format": cached_chat.get("parser_format") or "unknown",
                "detected_language": cached_chat.get("detected_language") or "unknown",
                "chat_stats_df": chat_stats_df,
                "chat_stats_json": chat_stats_json,
                "summary_html_path": str(html_path),
                "summary_json_path": str(json_path),
                "chat_id": cached_chat_id,
                "loaded_from_cache": True,
            }

    parsed = parse_chat(file_path=file_path, output_dir=output_dir)
    chat_stats_df = build_chat_stats(parsed["raw_data_df"])

    output_path = Path(parsed["output_dir"])
    raw_data_csv_path, html_path, json_path, chat_stats_json = _write_analysis_outputs(
        raw_data_df=parsed["raw_data_df"],
        chat_stats_df=chat_stats_df,
        output_path=output_path,
    )

    chat_id = None
    if persist:
        chat_id = store_analysis_result(
            file_path=file_path,
            raw_data_df=parsed["raw_data_df"],
            chat_stats_df=chat_stats_df,
            output_dir=parsed["output_dir"],
            parser_format=parsed.get("parser_format", "unknown"),
            detected_language=parsed.get("detected_language", "unknown"),
            db_path=db_path,
        )

    return {
        **parsed,
        "chat_stats_df": chat_stats_df,
        "chat_stats_json": chat_stats_json,
        "raw_data_csv_path": str(raw_data_csv_path),
        "summary_html_path": str(html_path),
        "summary_json_path": str(json_path),
        "chat_id": chat_id,
        "loaded_from_cache": False,
    }


def _write_analysis_outputs(
    *,
    raw_data_df: pd.DataFrame,
    chat_stats_df: pd.DataFrame,
    output_path: Path,
) -> tuple[Path, Path, Path, str]:
    output_path.mkdir(parents=True, exist_ok=True)

    raw_data_csv_path = output_path / "raw-data.csv"
    html_path = output_path / "summary.html"
    json_path = output_path / "summary.json"

    raw_data_df.to_csv(raw_data_csv_path, index=False)
    chat_stats_df.to_html(html_path, index=False)
    chat_stats_json = chat_stats_df.to_json(orient="records")
    json_path.write_text(chat_stats_json, encoding="utf-8")

    return raw_data_csv_path, html_path, json_path, chat_stats_json
