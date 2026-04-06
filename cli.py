import argparse

from app.analyzer import analyze_chat
from app.graphs import generate_graphs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze a WhatsApp chat export file (.txt)."
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="./data/chat.txt",
        help="Path to the WhatsApp chat export file",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Optional SQLite database path (defaults to KAAJD_DB_PATH or ./kaajd.sqlite3)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-analysis by ignoring the cached database version",
    )
    args = parser.parse_args()

    analysis = analyze_chat(
        args.file_path, db_path=args.db_path, reuse_cached=not args.force
    )
    generate_graphs(analysis["raw_data_df"], analysis["output_dir"])
    print(analysis["chat_stats_df"].to_string(index=False))


if __name__ == "__main__":
    main()
