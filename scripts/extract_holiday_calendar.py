"""Extract Finnish holiday calendar data from holiday-calendar.fi.

The script writes a normalized CSV and/or JSON file for a date range. By
default it fetches the 2025-2026 period, which is the first modelling window for
the Helsinki-Vantaa passenger forecast calendar features.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://holiday-calendar.fi/api/calendar"
DEFAULT_START = "2023-01-01"
DEFAULT_END = "2026-12-31"
DEFAULT_OUTPUT_DIR = Path("data/raw")
USER_AGENT = "helsinki-vantaa-calendar-research/0.1"


@dataclass(frozen=True)
class CalendarRow:
    date: str
    year: int
    month: int
    day: int
    weekday: int
    weekday_name: str
    working_day: bool
    description: str
    is_weekend: bool
    is_public_holiday: bool
    source: str


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD, for example 2025-01-01."
        ) from exc


def fetch_calendar(start: date, end: date, timeout: float, retries: int) -> dict[str, dict[str, Any]]:
    query = urlencode({"start": start.isoformat(), "end": end.isoformat()})
    url = f"{API_URL}?{query}"
    request = Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries:
                raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc
            time.sleep(min(2**attempt, 10))
            continue

        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected API response type: {type(payload).__name__}")

        return payload

    raise RuntimeError("Unreachable retry state")


def normalize_calendar(payload: dict[str, dict[str, Any]]) -> list[CalendarRow]:
    rows: list[CalendarRow] = []

    for iso_date in sorted(payload):
        value = payload[iso_date]
        current_date = parse_date(iso_date)
        description = str(value.get("desc", "")).strip()
        working_day = bool(value.get("working_day"))
        is_weekend = description.casefold() == "weekend"

        rows.append(
            CalendarRow(
                date=current_date.isoformat(),
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
                weekday=current_date.isoweekday(),
                weekday_name=current_date.strftime("%A"),
                working_day=working_day,
                description=description,
                is_weekend=is_weekend,
                is_public_holiday=(not working_day and not is_weekend),
                source=API_URL,
            )
        )

    return rows


def write_csv(rows: list[CalendarRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(CalendarRow.__dataclass_fields__)

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(rows: list[CalendarRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "source": API_URL,
        "rows": [asdict(row) for row in rows],
    }

    with path.open("w", encoding="utf-8") as output_file:
        json.dump(document, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract Finnish holiday calendar data from holiday-calendar.fi."
    )
    parser.add_argument("--start", type=parse_date, default=parse_date(DEFAULT_START))
    parser.add_argument("--end", type=parse_date, default=parse_date(DEFAULT_END))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated files. Defaults to data/raw.",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json", "both"),
        default="both",
        help="Output format to write. Defaults to both.",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.start > args.end:
        print("--start must be before or equal to --end", file=sys.stderr)
        return 2

    payload = fetch_calendar(args.start, args.end, timeout=args.timeout, retries=args.retries)
    rows = normalize_calendar(payload)

    stem = f"holiday_calendar_fi_{args.start.isoformat()}_{args.end.isoformat()}"
    written: list[Path] = []

    if args.format in {"csv", "both"}:
        csv_path = args.output_dir / f"{stem}.csv"
        write_csv(rows, csv_path)
        written.append(csv_path)

    if args.format in {"json", "both"}:
        json_path = args.output_dir / f"{stem}.json"
        write_json(rows, json_path)
        written.append(json_path)

    holiday_count = sum(row.is_public_holiday for row in rows)
    print(
        f"Fetched {len(rows)} dates, including {holiday_count} public holidays. "
        f"Wrote: {', '.join(str(path) for path in written)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
