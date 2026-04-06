import argparse
import sys

from app.analyzer import analyze_chat


DEPRECATION_NOTE = (
    "[deprecated] wa-stats.py is kept for compatibility. "
    "Use `python3 cli.py <chat.txt>` instead."
)


def main() -> None:
    print(DEPRECATION_NOTE, file=sys.stderr)
    parser = argparse.ArgumentParser(
        description="Analyze a WhatsApp chat export file (.txt)."
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="./data/chat.txt",
        help="Path to the chat export file",
    )
    args = parser.parse_args()

    analysis = analyze_chat(args.file_path)
    print(analysis["chat_stats_df"].to_string(index=False))


if __name__ == "__main__":
    main()
