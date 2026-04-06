from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def _default_db_path() -> Path:
    env_path = os.getenv("KAAJD_DB_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parent.parent / "kaajd.sqlite3"


def _connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    resolved = Path(db_path) if db_path is not None else _default_db_path()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(resolved)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db(db_path: str | Path | None = None) -> None:
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_hash TEXT NOT NULL UNIQUE,
                parser_format TEXT,
                detected_language TEXT,
                output_dir TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                system_message_count INTEGER NOT NULL DEFAULT 0,
                media_message_count INTEGER NOT NULL DEFAULT 0,
                link_message_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                message_index INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                person TEXT,
                message TEXT NOT NULL,
                is_system_message INTEGER NOT NULL DEFAULT 0,
                is_media_message INTEGER NOT NULL DEFAULT 0,
                has_link INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                UNIQUE(chat_id, message_index)
            );

            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                person TEXT NOT NULL,
                total_messages INTEGER NOT NULL,
                average_message_length REAL NOT NULL,
                total_characters INTEGER NOT NULL,
                is_total_row INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE,
                UNIQUE(chat_id, person, is_total_row)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
            CREATE INDEX IF NOT EXISTS idx_messages_person ON messages(person);
            CREATE INDEX IF NOT EXISTS idx_stats_chat_id ON stats(chat_id);
            """
        )


def build_source_hash(file_path: str | Path) -> str:
    return _sha256_file(Path(file_path).resolve())


def get_chat_by_source_hash(
    source_hash: str, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    init_db(db_path)
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM chats WHERE source_hash = ?",
            (source_hash,),
        ).fetchone()
    return dict(row) if row else None


def get_chat_by_output_dir(
    output_dir: str | Path, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    init_db(db_path)
    resolved_output_dir = str(Path(output_dir).resolve())
    with _connect(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM chats WHERE output_dir = ? ORDER BY updated_at DESC LIMIT 1",
            (resolved_output_dir,),
        ).fetchone()
    return dict(row) if row else None


def delete_chat(chat_id: int, db_path: str | Path | None = None) -> bool:
    init_db(db_path)
    with _connect(db_path) as connection:
        connection.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        connection.execute("DELETE FROM stats WHERE chat_id = ?", (chat_id,))
        cursor = connection.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        connection.commit()
        return cursor.rowcount > 0


def load_chat_frames(
    chat_id: int, db_path: str | Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    init_db(db_path)
    with _connect(db_path) as connection:
        message_rows = connection.execute(
            """
            SELECT
                date,
                time,
                person,
                message,
                is_system_message,
                is_media_message,
                has_link
            FROM messages
            WHERE chat_id = ?
            ORDER BY message_index
            """,
            (chat_id,),
        ).fetchall()

        stats_rows = connection.execute(
            """
            SELECT
                person,
                total_messages,
                average_message_length,
                total_characters,
                is_total_row
            FROM stats
            WHERE chat_id = ?
            ORDER BY is_total_row, person
            """,
            (chat_id,),
        ).fetchall()

    raw_data_df = pd.DataFrame(
        [
            {
                "Date": row["date"],
                "Time": row["time"],
                "Person": row["person"] or "",
                "Message": row["message"],
                "IsSystemMessage": bool(row["is_system_message"]),
                "IsMediaMessage": bool(row["is_media_message"]),
                "HasLink": bool(row["has_link"]),
            }
            for row in message_rows
        ]
    )

    chat_stats_df = pd.DataFrame(
        [
            {
                "Person": row["person"],
                "Total Messages": int(row["total_messages"]),
                "Average Message Length (chars)": float(row["average_message_length"]),
                "Total Characters": int(row["total_characters"]),
                "IsTotalRow": bool(row["is_total_row"]),
            }
            for row in stats_rows
        ]
    )

    if not chat_stats_df.empty and "IsTotalRow" in chat_stats_df.columns:
        chat_stats_df = chat_stats_df.drop(columns=["IsTotalRow"])

    return raw_data_df, chat_stats_df


def get_chat_context(
    chat_id: int, db_path: str | Path | None = None
) -> dict[str, Any] | None:
    init_db(db_path)
    with _connect(db_path) as connection:
        chat_row = connection.execute(
            "SELECT * FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone()
        if not chat_row:
            return None

        top_people_rows = connection.execute(
            """
            SELECT person, total_messages, average_message_length, total_characters
            FROM stats
            WHERE chat_id = ? AND is_total_row = 0
            ORDER BY total_messages DESC
            LIMIT 10
            """,
            (chat_id,),
        ).fetchall()

        total_row = connection.execute(
            """
            SELECT total_messages, average_message_length, total_characters
            FROM stats
            WHERE chat_id = ? AND is_total_row = 1
            LIMIT 1
            """,
            (chat_id,),
        ).fetchone()

        date_bounds_row = connection.execute(
            """
            SELECT
                MIN(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS min_date,
                MAX(substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2)) AS max_date
            FROM messages
            WHERE chat_id = ? AND is_system_message = 0
            """,
            (chat_id,),
        ).fetchone()

    chat = dict(chat_row)
    top_people = [dict(row) for row in top_people_rows]

    return {
        "chat": {
            "id": int(chat["id"]),
            "source_name": chat["source_name"],
            "source_path": chat["source_path"],
            "source_hash": chat["source_hash"],
            "parser_format": chat["parser_format"] or "unknown",
            "detected_language": chat["detected_language"] or "unknown",
            "output_dir": chat["output_dir"],
            "message_count": int(chat["message_count"]),
            "system_message_count": int(chat["system_message_count"]),
            "media_message_count": int(chat["media_message_count"]),
            "link_message_count": int(chat["link_message_count"]),
            "created_at": chat["created_at"],
            "updated_at": chat["updated_at"],
        },
        "totals": {
            "total_messages": int(total_row["total_messages"]) if total_row else 0,
            "average_message_length": float(total_row["average_message_length"])
            if total_row
            else 0.0,
            "total_characters": int(total_row["total_characters"]) if total_row else 0,
        },
        "top_people": [
            {
                "person": row["person"],
                "total_messages": int(row["total_messages"]),
                "average_message_length": float(row["average_message_length"]),
                "total_characters": int(row["total_characters"]),
            }
            for row in top_people
        ],
        "date_bounds": {
            "start_date": date_bounds_row["min_date"] if date_bounds_row else None,
            "end_date": date_bounds_row["max_date"] if date_bounds_row else None,
        },
    }


def list_recent_chats(
    *, limit: int = 10, db_path: str | Path | None = None
) -> list[dict[str, Any]]:
    init_db(db_path)
    with _connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                source_name,
                parser_format,
                detected_language,
                output_dir,
                message_count,
                created_at,
                updated_at
            FROM chats
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()

    return [dict(row) for row in rows]


def store_analysis_result(
    *,
    file_path: str | Path,
    raw_data_df: pd.DataFrame,
    chat_stats_df: pd.DataFrame,
    output_dir: str | Path,
    parser_format: str,
    detected_language: str,
    db_path: str | Path | None = None,
) -> int:
    init_db(db_path)

    resolved_file = Path(file_path).resolve()
    now = datetime.now(timezone.utc).isoformat()
    source_hash = build_source_hash(resolved_file)
    output_dir_value = str(Path(output_dir).resolve())

    message_count = int(len(raw_data_df))
    system_message_count = int(
        raw_data_df.get("IsSystemMessage", pd.Series(dtype=bool)).sum()
    )
    media_message_count = int(
        raw_data_df.get("IsMediaMessage", pd.Series(dtype=bool)).sum()
    )
    link_message_count = int(raw_data_df.get("HasLink", pd.Series(dtype=bool)).sum())

    with _connect(db_path) as connection:
        existing = connection.execute(
            "SELECT id FROM chats WHERE source_hash = ?",
            (source_hash,),
        ).fetchone()

        if existing:
            chat_id = int(existing["id"])
            connection.execute(
                """
                UPDATE chats
                SET source_name = ?,
                    source_path = ?,
                    parser_format = ?,
                    detected_language = ?,
                    output_dir = ?,
                    message_count = ?,
                    system_message_count = ?,
                    media_message_count = ?,
                    link_message_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    resolved_file.name,
                    str(resolved_file),
                    parser_format,
                    detected_language,
                    output_dir_value,
                    message_count,
                    system_message_count,
                    media_message_count,
                    link_message_count,
                    now,
                    chat_id,
                ),
            )
            connection.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            connection.execute("DELETE FROM stats WHERE chat_id = ?", (chat_id,))
        else:
            cursor = connection.execute(
                """
                INSERT INTO chats (
                    source_name,
                    source_path,
                    source_hash,
                    parser_format,
                    detected_language,
                    output_dir,
                    message_count,
                    system_message_count,
                    media_message_count,
                    link_message_count,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolved_file.name,
                    str(resolved_file),
                    source_hash,
                    parser_format,
                    detected_language,
                    output_dir_value,
                    message_count,
                    system_message_count,
                    media_message_count,
                    link_message_count,
                    now,
                    now,
                ),
            )
            row_id = cursor.lastrowid
            if row_id is None:
                raise RuntimeError("Failed to insert chat row")
            chat_id = int(row_id)

        message_rows = _messages_to_records(
            chat_id=chat_id, raw_data_df=raw_data_df, timestamp=now
        )
        if message_rows:
            connection.executemany(
                """
                INSERT INTO messages (
                    chat_id,
                    message_index,
                    date,
                    time,
                    person,
                    message,
                    is_system_message,
                    is_media_message,
                    has_link,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                message_rows,
            )

        stats_rows = _stats_to_records(
            chat_id=chat_id, chat_stats_df=chat_stats_df, timestamp=now
        )
        if stats_rows:
            connection.executemany(
                """
                INSERT INTO stats (
                    chat_id,
                    person,
                    total_messages,
                    average_message_length,
                    total_characters,
                    is_total_row,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                stats_rows,
            )

    return chat_id


def query_messages(
    chat_id: int,
    *,
    person: str | None = None,
    has_link: bool | None = None,
    is_media_message: bool | None = None,
    limit: int = 200,
    offset: int = 0,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    clauses = ["chat_id = ?"]
    params: list[Any] = [chat_id]

    if person is not None:
        clauses.append("person = ?")
        params.append(person)
    if has_link is not None:
        clauses.append("has_link = ?")
        params.append(int(has_link))
    if is_media_message is not None:
        clauses.append("is_media_message = ?")
        params.append(int(is_media_message))

    params.extend([max(1, int(limit)), max(0, int(offset))])
    where_clause = " AND ".join(clauses)

    with _connect(db_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                chat_id,
                message_index,
                date,
                time,
                person,
                message,
                is_system_message,
                is_media_message,
                has_link,
                created_at
            FROM messages
            WHERE {where_clause}
            ORDER BY message_index
            LIMIT ? OFFSET ?
            """,
            tuple(params),
        ).fetchall()

    return [dict(row) for row in rows]


def _sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _messages_to_records(
    *, chat_id: int, raw_data_df: pd.DataFrame, timestamp: str
) -> list[tuple[Any, ...]]:
    records: list[tuple[Any, ...]] = []
    for index, row in raw_data_df.reset_index(drop=True).iterrows():
        records.append(
            (
                chat_id,
                int(index),
                str(row.get("Date", "")),
                str(row.get("Time", "")),
                str(row.get("Person", "")),
                str(row.get("Message", "")),
                int(bool(row.get("IsSystemMessage", False))),
                int(bool(row.get("IsMediaMessage", False))),
                int(bool(row.get("HasLink", False))),
                timestamp,
            )
        )
    return records


def _stats_to_records(
    *, chat_id: int, chat_stats_df: pd.DataFrame, timestamp: str
) -> list[tuple[Any, ...]]:
    records: list[tuple[Any, ...]] = []
    for _, row in chat_stats_df.iterrows():
        person = str(row.get("Person", ""))
        records.append(
            (
                chat_id,
                person,
                int(row.get("Total Messages", 0)),
                float(row.get("Average Message Length (chars)", 0.0)),
                int(row.get("Total Characters", 0)),
                int(person == "Total (All Persons)"),
                timestamp,
            )
        )
    return records
