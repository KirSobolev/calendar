"""Build date-level school holiday features from curated OPH school terms."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_INPUTS = [
    Path("data/raw/oph_school_terms_2023_2024.csv"),
    Path("data/raw/oph_school_terms_2025_2026.csv"),
]
DEFAULT_POPULATION_INPUT = Path("data/raw/municipality_population_2024.csv")
DEFAULT_START = "2023-01-01"
DEFAULT_END = "2026-12-31"
DEFAULT_OUTPUT_DIR = Path("data/processed")


BREAK_COLUMNS = {
    "autumn_break": ("autumn_break_start", "autumn_break_end"),
    "christmas_break": ("christmas_break_start", "christmas_break_end"),
    "winter_break": ("winter_break_start", "winter_break_end"),
}

TERM_EVENT_COLUMNS = {
    "school_start": "school_start",
    "school_end": "school_end",
}


@dataclass(frozen=True)
class MunicipalityBreakRow:
    date: str
    municipality: str
    school_year: str
    holiday_type: str
    population: int
    population_weight: float
    source_url: str


@dataclass(frozen=True)
class MunicipalityTermEventRow:
    date: str
    municipality: str
    school_year: str
    event_type: str
    population: int
    population_weight: float
    source_url: str


@dataclass(frozen=True)
class DailySchoolHolidayFeatureRow:
    date: str
    year: int
    month: int
    day: int
    weekday: int
    weekday_name: str
    is_school_holiday_anywhere: bool
    school_holiday_municipality_count: int
    school_holiday_population: int
    school_holiday_population_weight: float
    school_holiday_types: str
    school_holiday_municipalities: str
    is_autumn_break_anywhere: bool
    autumn_break_municipality_count: int
    autumn_break_population: int
    autumn_break_population_weight: float
    is_christmas_break_anywhere: bool
    christmas_break_municipality_count: int
    christmas_break_population: int
    christmas_break_population_weight: float
    is_winter_break_anywhere: bool
    winter_break_municipality_count: int
    winter_break_population: int
    winter_break_population_weight: float
    school_start_municipalities: str
    school_start_population: int
    school_start_population_weight: float
    school_end_municipalities: str
    school_end_population: int
    school_end_population_weight: float
    source: str


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=offset) for offset in range(days + 1)]


def read_school_terms(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for path in paths:
        with path.open(newline="", encoding="utf-8") as input_file:
            rows.extend(csv.DictReader(input_file))

    return rows


def read_population_weights(path: Path) -> dict[str, dict[str, float | int]]:
    with path.open(newline="", encoding="utf-8") as input_file:
        rows = list(csv.DictReader(input_file))

    populations = {row["municipality"]: int(row["population"]) for row in rows}
    total_population = sum(populations.values())

    if total_population <= 0:
        raise ValueError("Total population must be positive")

    return {
        municipality: {
            "population": population,
            "population_weight": population / total_population,
        }
        for municipality, population in populations.items()
    }


def get_population(
    municipality: str, population_weights: dict[str, dict[str, float | int]]
) -> tuple[int, float]:
    if municipality not in population_weights:
        raise ValueError(f"Missing population for municipality: {municipality}")

    population = int(population_weights[municipality]["population"])
    population_weight = float(population_weights[municipality]["population_weight"])
    return population, population_weight


def expand_breaks(
    rows: list[dict[str, str]], population_weights: dict[str, dict[str, float | int]]
) -> list[MunicipalityBreakRow]:
    expanded: list[MunicipalityBreakRow] = []

    for row in rows:
        population, population_weight = get_population(row["municipality"], population_weights)
        for holiday_type, (start_column, end_column) in BREAK_COLUMNS.items():
            for current_date in date_range(parse_date(row[start_column]), parse_date(row[end_column])):
                expanded.append(
                    MunicipalityBreakRow(
                        date=current_date.isoformat(),
                        municipality=row["municipality"],
                        school_year=row["school_year"],
                        holiday_type=holiday_type,
                        population=population,
                        population_weight=population_weight,
                        source_url=row["source_url"],
                    )
                )

    return sorted(expanded, key=lambda item: (item.date, item.municipality, item.holiday_type))


def expand_term_events(
    rows: list[dict[str, str]], population_weights: dict[str, dict[str, float | int]]
) -> list[MunicipalityTermEventRow]:
    expanded: list[MunicipalityTermEventRow] = []

    for row in rows:
        population, population_weight = get_population(row["municipality"], population_weights)
        for event_type, source_column in TERM_EVENT_COLUMNS.items():
            expanded.append(
                MunicipalityTermEventRow(
                    date=row[source_column],
                    municipality=row["municipality"],
                    school_year=row["school_year"],
                    event_type=event_type,
                    population=population,
                    population_weight=population_weight,
                    source_url=row["source_url"],
                )
            )

    return sorted(expanded, key=lambda item: (item.date, item.municipality, item.event_type))


def build_daily_features(
    break_rows: list[MunicipalityBreakRow],
    event_rows: list[MunicipalityTermEventRow],
    start: date,
    end: date,
) -> list[DailySchoolHolidayFeatureRow]:
    breaks_by_date: dict[str, list[MunicipalityBreakRow]] = defaultdict(list)
    events_by_date: dict[str, list[MunicipalityTermEventRow]] = defaultdict(list)

    for row in break_rows:
        breaks_by_date[row.date].append(row)

    for row in event_rows:
        events_by_date[row.date].append(row)

    features: list[DailySchoolHolidayFeatureRow] = []

    for current_date in date_range(start, end):
        iso_date = current_date.isoformat()
        date_breaks = breaks_by_date[iso_date]
        date_events = events_by_date[iso_date]
        municipalities = sorted({row.municipality for row in date_breaks})
        holiday_types = sorted({row.holiday_type for row in date_breaks})
        counts_by_type = {
            holiday_type: len({row.municipality for row in date_breaks if row.holiday_type == holiday_type})
            for holiday_type in BREAK_COLUMNS
        }
        population_by_type = {
            holiday_type: sum(
                row.population for row in date_breaks if row.holiday_type == holiday_type
            )
            for holiday_type in BREAK_COLUMNS
        }
        population_weight_by_type = {
            holiday_type: sum(
                row.population_weight
                for row in date_breaks
                if row.holiday_type == holiday_type
            )
            for holiday_type in BREAK_COLUMNS
        }
        municipalities_by_event = {
            event_type: sorted(
                {row.municipality for row in date_events if row.event_type == event_type}
            )
            for event_type in TERM_EVENT_COLUMNS
        }
        population_by_event = {
            event_type: sum(row.population for row in date_events if row.event_type == event_type)
            for event_type in TERM_EVENT_COLUMNS
        }
        population_weight_by_event = {
            event_type: sum(
                row.population_weight for row in date_events if row.event_type == event_type
            )
            for event_type in TERM_EVENT_COLUMNS
        }
        sources = sorted({row.source_url for row in date_breaks + date_events})

        features.append(
            DailySchoolHolidayFeatureRow(
                date=iso_date,
                year=current_date.year,
                month=current_date.month,
                day=current_date.day,
                weekday=current_date.isoweekday(),
                weekday_name=current_date.strftime("%A"),
                is_school_holiday_anywhere=bool(date_breaks),
                school_holiday_municipality_count=len(municipalities),
                school_holiday_population=sum(row.population for row in date_breaks),
                school_holiday_population_weight=round(
                    sum(row.population_weight for row in date_breaks), 6
                ),
                school_holiday_types=";".join(holiday_types),
                school_holiday_municipalities=";".join(municipalities),
                is_autumn_break_anywhere=counts_by_type["autumn_break"] > 0,
                autumn_break_municipality_count=counts_by_type["autumn_break"],
                autumn_break_population=population_by_type["autumn_break"],
                autumn_break_population_weight=round(
                    population_weight_by_type["autumn_break"], 6
                ),
                is_christmas_break_anywhere=counts_by_type["christmas_break"] > 0,
                christmas_break_municipality_count=counts_by_type["christmas_break"],
                christmas_break_population=population_by_type["christmas_break"],
                christmas_break_population_weight=round(
                    population_weight_by_type["christmas_break"], 6
                ),
                is_winter_break_anywhere=counts_by_type["winter_break"] > 0,
                winter_break_municipality_count=counts_by_type["winter_break"],
                winter_break_population=population_by_type["winter_break"],
                winter_break_population_weight=round(
                    population_weight_by_type["winter_break"], 6
                ),
                school_start_municipalities=";".join(municipalities_by_event["school_start"]),
                school_start_population=population_by_event["school_start"],
                school_start_population_weight=round(
                    population_weight_by_event["school_start"], 6
                ),
                school_end_municipalities=";".join(municipalities_by_event["school_end"]),
                school_end_population=population_by_event["school_end"],
                school_end_population_weight=round(
                    population_weight_by_event["school_end"], 6
                ),
                source=";".join(sources),
            )
        )

    return features


def write_csv(rows: list[object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        raise ValueError(f"No rows to write for {path}")

    fieldnames = list(rows[0].__dataclass_fields__)  # type: ignore[attr-defined]

    with path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def write_json(rows: list[object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as output_file:
        json.dump([asdict(row) for row in rows], output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build date-level school holiday features from curated OPH school terms."
    )
    parser.add_argument(
        "--input",
        type=Path,
        nargs="+",
        default=DEFAULT_INPUTS,
        help="One or more curated OPH school-term CSV files.",
    )
    parser.add_argument("--population-input", type=Path, default=DEFAULT_POPULATION_INPUT)
    parser.add_argument("--start", type=parse_date, default=parse_date(DEFAULT_START))
    parser.add_argument("--end", type=parse_date, default=parse_date(DEFAULT_END))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.start > args.end:
        raise SystemExit("--start must be before or equal to --end")

    school_terms = read_school_terms(args.input)
    population_weights = read_population_weights(args.population_input)
    break_rows = expand_breaks(school_terms, population_weights)
    event_rows = expand_term_events(school_terms, population_weights)
    daily_features = build_daily_features(break_rows, event_rows, args.start, args.end)

    suffix = f"{args.start.isoformat()}_{args.end.isoformat()}"
    write_csv(break_rows, args.output_dir / f"school_holiday_municipality_dates_{suffix}.csv")
    write_csv(event_rows, args.output_dir / f"school_term_events_{suffix}.csv")
    write_csv(daily_features, args.output_dir / f"school_holiday_features_{suffix}.csv")
    write_json(daily_features, args.output_dir / f"school_holiday_features_{suffix}.json")

    holiday_dates = sum(row.is_school_holiday_anywhere for row in daily_features)
    unique_municipality_count = len({row["municipality"] for row in school_terms})
    print(
        f"Processed {len(school_terms)} school-term rows across "
        f"{unique_municipality_count} municipalities. "
        f"Expanded {len(break_rows)} municipality-holiday date rows. "
        f"Built {len(daily_features)} daily feature rows, with {holiday_dates} dates "
        "covered by at least one school holiday."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
