# Portfolio Management

A unified setup for:

1. **Market Collector**
   - one Dockerized Python 3.12 collector project
   - crawls local-market sources
   - fetches macro/market series using `fredapi`
   - stores each dataset/series in its own CSV inside `market_collector/outputs/`
   - each output CSV contains **weekly rows**
   - all weekly rows use **Monday of the week** as `date`

2. **Portfolio Management Dashboard**
   - one Dockerized FastAPI dashboard
   - reads weekly CSV outputs from the unified collector
   - merges all datasets on weekly `date`
   - computes Gold / SJC / VN30 indicators from weekly data
   - renders a single-page dashboard with tabs, charts, and data tables
   - explicitly displays **weekly dates** on charts and tables

This README documents the **overall system architecture**.

---

# Part 1 — Unified Architecture

## Overview

The old design used multiple sibling collector projects such as:

- `imir_collector`
- `gold_collector`
- `sjc_collector`
- `usty_collector`
- `vn30_collector`

The new design replaces them with **one unified collector project**:

- `market_collector/`

The dashboard reads data from:

- `../market_collector/outputs/*.csv`

---

## Final data flow

### Collector responsibilities

The collector handles:

#### Crawl sources
- `imir`
- `vn30`
- `sjc`

#### FRED sources
- `gold`
- `dxy`
- `vix`
- `wti`
- `sp500`
- `stoxx`
- `us3m`
- `us2y`
- `us10y`
- `us30y`

### Dashboard responsibilities

The dashboard:

- reads the collector CSV files
- merges them on weekly `date`
- filters by selected date range
- computes Gold / SJC / VN30 indicators
- displays weekly charts and weekly data tables in one page

---

# Part 2 — Final Project Structure

```bash
a_portfolio_management/
├── README.md
├── market_collector/
│   ├── README.md
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── market_collector.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── fred_collector.py
│   │   ├── imir.py
│   │   ├── vn30.py
│   │   └── sjc.py
│   ├── outputs/
│   ├── errors/
│   └── ...
└── dashboard/
    ├── README.md
    ├── dashboard.py
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    └── __init__.py
```

---

# Part 3 — Weekly Data Standard

All collector outputs use:

- **one row per week**
- `date` = **Monday of the week**

## Final weekly standard used by this project

This project uses the following weekly setup:

- `imir` uses **week-start Monday**
- `vn30` uses **week-start Monday**
- `sjc` daily values are grouped into **week-start Monday** buckets
- `fredapi` data is fetched and normalized into **weekly Monday rows**
- saved `date` for all outputs is the **Monday of the week**

## Monday mapping rule

For Monday-based weekly collectors:

- if the source date is Monday, use that same Monday
- if the source date is Tuesday through Sunday, map back to the most recent Monday
- do not map to a future date

This gives a complete Monday-based weekly solution for local-market collectors and FRED-based market series.

---

# Part 4 — Run Model

## Collector operating model

- `--all` runs **all crawl tasks only**
  - `imir`
  - `vn30`
  - `sjc`

- FRED tasks must be run with `--only`

### Recommended incremental examples

```bash
python market_collector.py --only gold --fred-mode incremental
python market_collector.py --only dxy --fred-mode incremental
python market_collector.py --only wti --fred-mode incremental
```

### Recommended full-history examples

```bash
python market_collector.py --only gold --fred-mode full
python market_collector.py --only dxy --fred-mode full
python market_collector.py --only wti --fred-mode full
```

## Production recommendation

- run crawl tasks together using `--all`
- run FRED series individually using `--only`
- schedule periodic incremental refreshes

---

# Part 5 — Run Instructions

## Run collector

From inside the `market_collector/` folder:

```bash
docker compose up --build
```

This default command runs:

```bash
python market_collector.py --all
```

## Run dashboard

From inside the `dashboard/` folder:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000/
```

---

# Part 6 — Documentation Map

For detailed component documentation, see:

- root system overview:
  - `README.md`
- collector details:
  - `market_collector/README.md`
- dashboard details:
  - `dashboard/README.md`

---

# Part 7 — Notes

## Collector notes

- crawl tasks:
  - `imir`
  - `vn30`
  - `sjc`
- FRED tasks:
  - `gold`
  - `dxy`
  - `vix`
  - `wti`
  - `sp500`
  - `stoxx`
  - `us3m`
  - `us2y`
  - `us10y`
  - `us30y`
- each dataset/series writes to its own CSV file
- each output CSV contains weekly rows
- all weekly outputs use **Monday of the week** as `date`

## Dashboard notes

- dashboard reads local CSV files only
- dashboard does not fetch remote sources directly
- dashboard assumes source CSV files are already weekly
- dashboard sorts and de-duplicates rows by weekly `date` before merge
- main dashboard charts use actual weekly Monday dates on the x-axis
- YoY calculations use 52 weekly periods

---

# License

Personal/internal use.
