# Helsinki-Vantaa Calendar Features

Research tooling for building date-based features for Helsinki-Vantaa flight
passenger forecasting.

## Extract Finnish Public Holidays

Fetch calendar data from [holiday-calendar.fi](https://holiday-calendar.fi/):

```powershell
python scripts/extract_holiday_calendar.py
```

The script writes:

- `data/raw/holiday_calendar_fi_<start>_<end>.csv`
- `data/raw/holiday_calendar_fi_<start>_<end>.json`

Use a custom range when needed:

```powershell
python scripts/extract_holiday_calendar.py --start 2023-01-01 --end 2026-12-31
```

The normalized output includes weekday fields, `working_day`,
`is_public_holiday`, `is_weekend`, and the original holiday description from the
API.

## Build School Holiday Features

The OPH school-term articles have been curated into:

- `data/raw/oph_school_terms_2023_2024.csv`
- `data/raw/oph_school_terms_2024_2025.csv`
- `data/raw/oph_school_terms_2025_2026.csv`

Municipality populations are kept separately in:

- `data/raw/municipality_population_2024.csv`

Expand it into model-ready daily features:

```powershell
python scripts/build_school_holiday_features.py
```

The script writes:

- `data/processed/school_holiday_municipality_dates_2023-01-01_2026-12-31.csv`
- `data/processed/school_term_events_2023-01-01_2026-12-31.csv`
- `data/processed/school_holiday_features_2023-01-01_2026-12-31.csv`
- `data/processed/school_holiday_features_2023-01-01_2026-12-31.json`

The daily feature output includes whether any listed municipality is on school
holiday, municipality counts and population-weighted shares by break type,
municipality lists, and school start/end event markers.

## Build Combined Calendar Features

Join public holidays and school holidays into one daily table:

```powershell
python scripts/build_calendar_features.py
```

The script writes:

- `data/processed/calendar_features_2025-01-01_2026-12-31.csv`
- `data/processed/calendar_features_2023-01-01_2026-12-31.csv`

## Static Calendar Webpage

The GitHub Pages-ready static site lives in `docs/`.

- `docs/index.html`
- `docs/styles.css`
- `docs/app.js`
- `docs/data/calendar_features_2023-01-01_2026-12-31.csv`
- `docs/data/calendar_features.js`

Configure GitHub Pages to serve from the repository's `docs/` folder. The page
uses only static files and browser-side JavaScript. No backend is required.

The embedded `calendar_features.js` copy lets the page work when opened directly
from disk. The CSV remains alongside it as the auditable data artifact.

After rebuilding `data/processed/calendar_features_2023-01-01_2026-12-31.csv`,
refresh the static site data files with:

```powershell
node scripts/build_static_site_data.js
```
