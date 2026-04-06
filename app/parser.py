from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path

import pandas as pd

langdetect_module = None

try:
    import langdetect
    from langdetect import DetectorFactory

    langdetect_module = langdetect
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False


@dataclass(frozen=True)
class PatternSpec:
    name: str
    line_pattern: re.Pattern[str]
    datetime_formats: tuple[str, ...]


PATTERN_SPECS = (
    PatternSpec(
        name="android_bracketed",
        line_pattern=re.compile(
            r"^\[(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}), (?P<time>\d{2}:\d{2}(?::\d{2})?)\] (?P<body>.*)$"
        ),
        datetime_formats=(
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%m/%d/%y %H:%M:%S",
            "%m/%d/%y %H:%M",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d/%m/%y %H:%M:%S",
            "%d/%m/%y %H:%M",
        ),
    ),
    PatternSpec(
        name="dutch_dd-mm-yyyy",
        line_pattern=re.compile(
            r"^(?P<date>\d{2}-\d{2}-\d{4}) (?P<time>\d{2}:\d{2}) - (?P<body>.*)$"
        ),
        datetime_formats=("%d-%m-%Y %H:%M",),
    ),
    PatternSpec(
        name="uk_dd-mm-yyyy_comma",
        line_pattern=re.compile(
            r"^(?P<date>\d{1,2}/\d{1,2}/\d{4}), (?P<time>\d{2}:\d{2}) - (?P<body>.*)$"
        ),
        datetime_formats=("%d/%m/%Y %H:%M",),
    ),
    PatternSpec(
        name="us_mm-dd-yy_comma",
        line_pattern=re.compile(
            r"^(?P<date>\d{1,2}/\d{1,2}/\d{2,4}), (?P<time>\d{2}:\d{2}) - (?P<body>.*)$"
        ),
        datetime_formats=("%m/%d/%y %H:%M", "%m/%d/%Y %H:%M"),
    ),
)

LINK_PATTERN = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
MEDIA_MESSAGES = {"<media weggelaten>", "<media omitted>"}


def _resolve_output_dir(file_path: Path, output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        resolved = Path(output_dir)
    else:
        resolved = file_path.parent / file_path.stem / "output"
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def parse_chat(file_path: str | Path, output_dir: str | Path | None = None) -> dict:
    source_file = Path(file_path)
    resolved_output_dir = _resolve_output_dir(source_file, output_dir)

    with source_file.open("r", encoding="utf-8") as file:
        all_lines = file.readlines()

    selected_pattern = _detect_pattern(all_lines)
    raw_data: list[list[str | bool]] = []

    previous_line = ""
    for line in all_lines:
        if _matches_pattern(line, selected_pattern):
            if previous_line:
                _append_message_row(previous_line, raw_data, selected_pattern)
            previous_line = line
        else:
            previous_line += line

    if previous_line:
        _append_message_row(previous_line, raw_data, selected_pattern)

    raw_data_df = pd.DataFrame(
        raw_data,
        columns=[
            "Date",
            "Time",
            "Person",
            "Message",
            "IsSystemMessage",
            "IsMediaMessage",
            "HasLink",
        ],
    )

    # Exclude bots/AI globally
    if not raw_data_df.empty:
        raw_data_df = raw_data_df[~raw_data_df["Person"].str.lower().isin({"meta ai"})]

    detected_language = _detect_language(raw_data_df)
    raw_data_csv_path = resolved_output_dir / "raw-data.csv"
    raw_data_df.to_csv(raw_data_csv_path, index=False)

    return {
        "raw_data_df": raw_data_df,
        "output_dir": str(resolved_output_dir),
        "raw_data_csv_path": str(raw_data_csv_path),
        "parser_format": selected_pattern.name,
        "detected_language": detected_language,
    }


def _detect_pattern(lines: list[str]) -> PatternSpec:
    sample_lines = [line.strip("\n") for line in lines if line.strip()][:5]
    if not sample_lines:
        return PATTERN_SPECS[1]

    best_pattern = PATTERN_SPECS[0]
    best_score = -1
    for spec in PATTERN_SPECS:
        score = sum(
            1 for line in sample_lines if _parse_message_header(line, spec) is not None
        )
        if score > best_score:
            best_score = score
            best_pattern = spec

    return best_pattern


def _matches_pattern(line: str, spec: PatternSpec) -> bool:
    return _parse_message_header(line.strip("\n"), spec) is not None


def _append_message_row(
    message_block: str, raw_data: list[list[str | bool]], spec: PatternSpec
) -> None:
    lines = message_block.splitlines()
    if not lines:
        return

    parsed_header = _parse_message_header(lines[0], spec)
    if parsed_header is None:
        return

    timestamp, body = parsed_header
    continuation = "\n".join(lines[1:]).rstrip("\n")
    if ": " in body:
        person_name, message = body.split(": ", 1)
        is_system_message = False
    else:
        person_name = ""
        message = body
        is_system_message = True

    if continuation:
        message = f"{message}\n{continuation}"

    message_clean = message.rstrip("\n")
    normalized = message_clean.strip().lower()
    is_media_message = normalized in MEDIA_MESSAGES
    has_link = bool(LINK_PATTERN.search(message_clean))

    raw_data.append(
        [
            timestamp.strftime("%d-%m-%Y"),
            timestamp.strftime("%H:%M"),
            person_name,
            message_clean,
            is_system_message,
            is_media_message,
            has_link,
        ]
    )


def _parse_message_header(line: str, spec: PatternSpec) -> tuple[datetime, str] | None:
    match = spec.line_pattern.match(line)
    if match is None:
        return None

    date_part = match.group("date")
    time_part = match.group("time")
    body = match.group("body")
    parsed_datetime = _parse_datetime(
        date_part=date_part, time_part=time_part, formats=spec.datetime_formats
    )
    if parsed_datetime is None:
        return None

    return parsed_datetime, body


def _parse_datetime(
    date_part: str, time_part: str, formats: tuple[str, ...]
) -> datetime | None:
    for fmt in formats:
        try:
            return datetime.strptime(f"{date_part} {time_part}", fmt)
        except ValueError:
            continue
    return None


def _detect_language(raw_data_df: pd.DataFrame) -> str:
    if not LANGDETECT_AVAILABLE or langdetect_module is None:
        return "unknown"

    text_df = raw_data_df.copy()
    if "IsSystemMessage" in text_df.columns:
        text_df = text_df[~text_df["IsSystemMessage"]]

    messages = [
        str(message).strip()
        for message in text_df.get("Message", pd.Series(dtype=str)).tolist()
        if str(message).strip()
    ]
    sample = " ".join(messages[:200])
    if len(sample) < 20:
        return "unknown"

    try:
        return langdetect_module.detect(sample)
    except Exception:
        return "unknown"
