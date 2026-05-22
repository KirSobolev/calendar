"""Join public-holiday and school-holiday features into one calendar table."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_PUBLIC_HOLIDAYS = Path("data/raw/holiday_calendar_fi_2023-01-01_2026-12-31.csv")
DEFAULT_SCHOOL_HOLIDAYS = Path(
    "data/processed/school_holiday_features_2023-01-01_2026-12-31.csv"
)
DEFAULT_OUTPUT = Path("data/processed/calendar_features_2023-01-01_2026-12-31.csv")


def read_csv_by_date(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))

    return {row["date"]: row for row in rows}


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write")

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def merge_features(
    public_holidays: dict[str, dict[str, str]],
    school_holidays: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    if set(public_holidays) != set(school_holidays):
        missing_from_school = sorted(set(public_holidays) - set(school_holidays))
        missing_from_public = sorted(set(school_holidays) - set(public_holidays))
        raise ValueError(
            "Input date ranges do not match. "
            f"Missing from school: {missing_from_school[:5]}. "
            f"Missing from public: {missing_from_public[:5]}."
        )

    merged: list[dict[str, str]] = []

    for iso_date in sorted(public_holidays):
        public_row = public_holidays[iso_date]
        school_row = school_holidays[iso_date]

        merged.append(
            {
                "date": iso_date,
                "year": public_row["year"],
                "month": public_row["month"],
                "day": public_row["day"],
                "weekday": public_row["weekday"],
                "weekday_name": public_row["weekday_name"],
                "working_day": public_row["working_day"],
                "holiday_description": public_row["description"],
                "is_weekend": public_row["is_weekend"],
                "is_public_holiday": public_row["is_public_holiday"],
                "is_school_holiday_anywhere": school_row["is_school_holiday_anywhere"],
                "school_holiday_municipality_count": school_row[
                    "school_holiday_municipality_count"
                ],
                "school_holiday_population": school_row["school_holiday_population"],
                "school_holiday_population_weight": school_row[
                    "school_holiday_population_weight"
                ],
                "school_holiday_types": school_row["school_holiday_types"],
                "school_holiday_municipalities": school_row["school_holiday_municipalities"],
                "is_autumn_break_anywhere": school_row["is_autumn_break_anywhere"],
                "autumn_break_municipality_count": school_row[
                    "autumn_break_municipality_count"
                ],
                "autumn_break_population": school_row["autumn_break_population"],
                "autumn_break_population_weight": school_row[
                    "autumn_break_population_weight"
                ],
                "is_christmas_break_anywhere": school_row["is_christmas_break_anywhere"],
                "christmas_break_municipality_count": school_row[
                    "christmas_break_municipality_count"
                ],
                "christmas_break_population": school_row["christmas_break_population"],
                "christmas_break_population_weight": school_row[
                    "christmas_break_population_weight"
                ],
                "is_winter_break_anywhere": school_row["is_winter_break_anywhere"],
                "winter_break_municipality_count": school_row[
                    "winter_break_municipality_count"
                ],
                "winter_break_population": school_row["winter_break_population"],
                "winter_break_population_weight": school_row[
                    "winter_break_population_weight"
                ],
                "school_start_municipalities": school_row["school_start_municipalities"],
                "school_start_population": school_row["school_start_population"],
                "school_start_population_weight": school_row[
                    "school_start_population_weight"
                ],
                "school_end_municipalities": school_row["school_end_municipalities"],
                "school_end_population": school_row["school_end_population"],
                "school_end_population_weight": school_row["school_end_population_weight"],
                "public_holiday_source": public_row["source"],
                "school_holiday_source": school_row["source"],
            }
        )

    return merged


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Join public-holiday and school-holiday features into one calendar table."
    )
    parser.add_argument("--public-holidays", type=Path, default=DEFAULT_PUBLIC_HOLIDAYS)
    parser.add_argument("--school-holidays", type=Path, default=DEFAULT_SCHOOL_HOLIDAYS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    public_holidays = read_csv_by_date(args.public_holidays)
    school_holidays = read_csv_by_date(args.school_holidays)
    merged = merge_features(public_holidays, school_holidays)
    write_csv(merged, args.output)
    print(f"Wrote {len(merged)} joined calendar feature rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
