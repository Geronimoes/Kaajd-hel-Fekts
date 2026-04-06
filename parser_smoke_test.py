from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.parser import parse_chat


CASES = (
    {
        "name": "dutch_dd-mm-yyyy",
        "content": (
            "05-04-2026 09:15 - Alice: Goedemorgen\n"
            "05-04-2026 09:16 - Bob: Hallo!\n"
            "05-04-2026 09:20 - Berichten en oproepen zijn end-to-end versleuteld.\n"
        ),
        "expected_format": "dutch_dd-mm-yyyy",
    },
    {
        "name": "uk_dd-mm-yyyy_comma",
        "content": (
            "05/04/2026, 09:15 - Alice: Morning\n05/04/2026, 09:16 - Bob: Hi there\n"
        ),
        "expected_format": "uk_dd-mm-yyyy_comma",
    },
    {
        "name": "us_mm-dd-yy_comma",
        "content": ("04/05/26, 09:15 - Alice: Morning\n04/05/26, 09:17 - Bob: Hey\n"),
        "expected_format": "us_mm-dd-yy_comma",
    },
    {
        "name": "android_bracketed",
        "content": (
            "[05-04-2026, 09:15:00] Alice: Message one\n"
            "[05-04-2026, 09:16:00] Bob: Message two\n"
        ),
        "expected_format": "android_bracketed",
    },
)


def run() -> None:
    failures: list[str] = []

    for case in CASES:
        temp_dir = Path(tempfile.mkdtemp(prefix="kaajd-smoke-"))
        try:
            file_path = temp_dir / "chat.txt"
            file_path.write_text(case["content"], encoding="utf-8")

            result = parse_chat(file_path)
            parser_format = result["parser_format"]
            if parser_format != case["expected_format"]:
                failures.append(
                    f"{case['name']}: expected {case['expected_format']}, got {parser_format}"
                )

            raw_df = result["raw_data_df"]
            if raw_df.empty:
                failures.append(f"{case['name']}: parser produced no rows")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    if failures:
        print("Parser smoke test failed:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Parser smoke test passed.")


if __name__ == "__main__":
    run()
