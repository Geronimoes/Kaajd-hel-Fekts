import argparse
from pathlib import Path
import sys

import pandas as pd

from app.analyzer import analyze_chat
from app.graphs import generate_graphs


DEPRECATION_NOTE = (
    "[deprecated] wa-graphs.py is kept for compatibility. "
    "Use `python3 cli.py <chat.txt>` for full analysis + graphs."
)


def _load_raw_data_if_available(file_path: str) -> tuple[pd.DataFrame | None, Path]:
    source_file = Path(file_path)
    output_dir = source_file.parent / source_file.stem / "output"
    raw_csv_path = output_dir / "raw-data.csv"
    if raw_csv_path.exists():
        return pd.read_csv(raw_csv_path), output_dir
    return None, output_dir


def main() -> None:
    print(DEPRECATION_NOTE, file=sys.stderr)
    parser = argparse.ArgumentParser(
        description="Generate graphs for a WhatsApp chat export file."
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="./data/chat.txt",
        help="Path to the chat export file",
    )
    args = parser.parse_args()

    raw_data_df, output_dir = _load_raw_data_if_available(args.file_path)
    if raw_data_df is None:
        analysis = analyze_chat(args.file_path)
        raw_data_df = analysis["raw_data_df"]
        output_dir = Path(analysis["output_dir"])

    generated = generate_graphs(raw_data_df, output_dir)
    for graph_file in generated:
        print(graph_file)


if __name__ == "__main__":
    main()
