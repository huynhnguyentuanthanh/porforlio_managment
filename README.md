# Portfolio Management + Market Collector

A unified setup for:

1. **Market Collector**
   - one Dockerized Python 3.12 collector project
   - crawls local-market sources
   - fetches macro/market series using `fredapi`
   - stores each dataset/series in its own CSV inside `outputs/`
   - each output CSV contains **weekly rows**
   - all weekly rows use **Monday of the week** as `date`

2. **Portfolio Management Dashboard**
   - one Dockerized FastAPI dashboard
   - reads weekly CSV outputs from the unified collector
   - merges all datasets on weekly `date`
   - computes Gold / SJC / VN30 indicators from weekly data
   - renders a single-page dashboard with tabs, charts, and data tables
   - explicitly displays **weekly dates** on charts and tables

This README documents the **weekly unified architecture** and includes the **full contents of all key files** for copy/paste.

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
- `gspc`
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
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── README.md
│   ├── market_collector.py
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── fred_collector.py
│   │   ├── imir.py
│   │   ├── vn30.py
│   │   └── sjc.py
│   ├── outputs/
│   │   ├── imir.csv
│   │   ├── vn30.csv
│   │   ├── sjc.csv
│   │   ├── gold.csv
│   │   ├── dxy.csv
│   │   ├── vix.csv
│   │   ├── wti.csv
│   │   ├── gspc.csv
│   │   ├── stoxx.csv
│   │   ├── us3m.csv
│   │   ├── us2y.csv
│   │   ├── us10y.csv
│   │   └── us30y.csv
│   └── errors/
│       ├── imir_error.html
│       └── vn30_error.html
└── dashboard/
    ├── dashboard.py
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    ├── README.md
    └── __init__.py
```

---

# Part 3 — Weekly Collector Design

## Output behavior

Each dataset/series is stored in its own CSV file under:

```bash
market_collector/outputs/
```

Each CSV contains **weekly rows**.

This means:

- `gold.csv` contains weekly gold rows
- `sjc.csv` contains weekly SJC rows
- `vn30.csv` contains weekly VN30 rows
- and so on

## Weekly standard

All collector outputs use:

- **one row per week**
- `date` = **Monday of the week** for that dataset

## Final weekly standard used by this project

This project uses the following weekly setup:

- `imir` uses **week-start Monday**
- `vn30` uses **week-start Monday**
- `sjc` daily values are grouped into **week-start Monday** buckets
- `fredapi` data is fetched and normalized into **weekly Monday rows**
- saved `date` for all outputs is the **Monday of the week**

### FRED weekly standard

For FRED series:

- data is fetched from FRED using `fredapi`
- the saved output is normalized to **one weekly row per Monday**
- if source observations are daily or business-daily, they are grouped into **Monday-based weekly buckets**
- the final saved `date` is always the **Monday of that week**
- the last available observation within each Monday-based week bucket is kept

### Snapshot collector weekly standard

For snapshot-based collectors such as `imir` and `vn30`:

- the current snapshot is mapped to the **Monday of the current week**
- repeated runs within the same week overwrite the same Monday row
- Monday through Sunday runs all map to the same week’s Monday
- snapshot collectors therefore use a **Monday-anchored weekly date**

### SJC weekly standard

For `sjc`:

- daily SJC observations are collected
- each observation is mapped to the **Monday of its week**
- the last available daily observation in each Monday-based week bucket is kept
- final saved output is therefore **weekly Monday-based data**

### Monday mapping rule

For Monday-based weekly collectors:

- if the source date is Monday, use that same Monday
- if the source date is Tuesday through Sunday, map back to the most recent Monday
- do not map to a future date

This gives a complete Monday-based weekly solution for local-market collectors and FRED-based market series.

---

# Part 4 — FRED Mapping

| Output name | FRED series id |
|---|---|
| `gold` | `GOLDPMGBD228NLBM` |
| `dxy` | `DTWEXBGS` |
| `vix` | `VIXCLS` |
| `wti` | `DCOILWTICO` |
| `gspc` | `SP500` |
| `stoxx` | `STOXX50E` |
| `us3m` | `TB3MS` |
| `us2y` | `DGS2` |
| `us10y` | `DGS10` |
| `us30y` | `DGS30` |

## Treasury normalization

Treasury yield series are normalized as raw percentage values already supplied by FRED, so:

- `us3m`
- `us2y`
- `us10y`
- `us30y`

do **not** require the Yahoo-style divide-by-10 normalization.

---

# Part 5 — FRED Operating Model

`fredapi` is used to fetch official macro/market series from FRED.

Compared with unofficial Yahoo access, this approach is more stable for programmatic collection of macro and rate data.

## Recommended rule

For FRED series, run **one series at a time** if desired for operational simplicity, but the collector logic can support individual or selected runs safely.

## CLI behavior used by this project

- `--all` runs **all crawl tasks only**
  - `imir`
  - `vn30`
  - `sjc`
- FRED tasks must be run with `--only`

### Recommended full-history pattern

```bash
python market_collector.py --only gold --fred-mode full
python market_collector.py --only dxy --fred-mode full
python market_collector.py --only wti --fred-mode full
```

### Recommended incremental pattern

```bash
python market_collector.py --only gold --fred-mode incremental
python market_collector.py --only dxy --fred-mode incremental
python market_collector.py --only wti --fred-mode incremental
```

## Production recommendation

- run crawl tasks together using `--all` if desired
- run FRED series individually using `--only`
- schedule periodic incremental refreshes

This keeps the collection model simple and consistent.

---

# Part 6 — File Contents

## 6.1 `market_collector/requirements.txt`

```txt
pandas==2.2.2
requests==2.32.3
fredapi==0.5.2
beautifulsoup4==4.12.3
selenium==4.24.0
```

---

## 6.2 `market_collector/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-liberation \
    ca-certificates \
    openssl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "market_collector.py", "--all"]
```

---

## 6.3 `market_collector/docker-compose.yml`

```yaml
services:
  market-collector:
    build: .
    container_name: market-collector
    working_dir: /app
    volumes:
      - .:/app
    environment:
      - FRED_API_KEY=${FRED_API_KEY}
    command: python market_collector.py --all
```

---

## 6.4 `market_collector/collectors/common.py`

```python
from pathlib import Path
import pandas as pd


OUTPUT_DIR = Path("outputs")
ERROR_DIR = Path("errors")


def ensure_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ERROR_DIR.mkdir(parents=True, exist_ok=True)


def load_existing_single_value_csv(path: Path, output_name: str) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=["date", output_name])

    df = pd.read_csv(path)

    required_cols = ["date", output_name]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{path} must include columns {required_cols}, got {df.columns.tolist()}")

    df = df[required_cols].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[output_name] = pd.to_numeric(df[output_name], errors="coerce")

    df = df.dropna(subset=["date", output_name]).sort_values("date")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def merge_and_save_single_value(existing_df: pd.DataFrame, new_df: pd.DataFrame, path: Path, output_name: str) -> pd.DataFrame:
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined[output_name] = pd.to_numeric(combined[output_name], errors="coerce")

    combined = combined.dropna(subset=["date", output_name])
    combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    combined.to_csv(path, index=False)
    return combined


def load_existing_multi_value_csv(path: Path, value_columns: list[str]) -> pd.DataFrame:
    expected_cols = ["date"] + value_columns

    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=expected_cols)

    df = pd.read_csv(path)

    missing = [col for col in expected_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{path} must include columns {expected_cols}, got {df.columns.tolist()}")

    df = df[expected_cols].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    for col in value_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["date"]).sort_values("date")
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df


def merge_and_save_multi_value(existing_df: pd.DataFrame, new_df: pd.DataFrame, path: Path, value_columns: list[str]) -> pd.DataFrame:
    expected_cols = ["date"] + value_columns

    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined = combined[expected_cols].copy()
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")

    for col in value_columns:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")

    combined = combined.dropna(subset=["date"])
    combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")
    combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")

    combined.to_csv(path, index=False)
    return combined


def get_week_monday(target_date) -> pd.Timestamp:
    ts = pd.to_datetime(target_date)
    return ts - pd.Timedelta(days=ts.weekday())


def map_single_value_to_weekly_monday(df: pd.DataFrame, output_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", output_name])

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data[output_name] = pd.to_numeric(data[output_name], errors="coerce")
    data = data.dropna(subset=["date", output_name]).sort_values("date")

    data["date"] = data["date"].apply(get_week_monday)

    weekly = (
        data.groupby("date", as_index=False)[output_name]
        .last()
        .sort_values("date")
    )

    weekly["date"] = weekly["date"].dt.strftime("%Y-%m-%d")
    return weekly[["date", output_name]]
```

---

## 6.5 `market_collector/collectors/fred_collector.py`

```python
from datetime import date
import os

import pandas as pd
from fredapi import Fred

from collectors.common import (
    OUTPUT_DIR,
    ensure_directories,
    load_existing_single_value_csv,
    merge_and_save_single_value,
    map_single_value_to_weekly_monday,
)


FRED_SERIES = {
    "gold": "GOLDPMGBD228NLBM",
    "dxy": "DTWEXBGS",
    "vix": "VIXCLS",
    "wti": "DCOILWTICO",
    "gspc": "SP500",
    "stoxx": "STOXX50E",
    "us3m": "TB3MS",
    "us2y": "DGS2",
    "us10y": "DGS10",
    "us30y": "DGS30",
}

FALLBACK_START_DATES = {
    "gold": "2000-01-01",
    "dxy": "2000-01-01",
    "vix": "1990-01-01",
    "wti": "2000-01-01",
    "gspc": "1971-01-01",
    "stoxx": "1986-01-01",
    "us3m": "1971-01-01",
    "us2y": "1971-01-01",
    "us10y": "1971-01-01",
    "us30y": "1977-01-01",
}


def get_fred_client() -> Fred:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set")
    return Fred(api_key=api_key)


def normalize_history(series: pd.Series, output_name: str) -> pd.DataFrame:
    if series.empty:
        return pd.DataFrame(columns=["date", output_name])

    df = series.reset_index()
    df.columns = ["date", output_name]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[output_name] = pd.to_numeric(df[output_name], errors="coerce")

    df = df.dropna(subset=["date", output_name]).sort_values("date")

    weekly = map_single_value_to_weekly_monday(df, output_name)
    return weekly


def fetch_fred_history(series_id: str, output_name: str, start_date: str, end_date: str) -> pd.DataFrame:
    fred = get_fred_client()
    series = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)

    print(f"[{output_name}] Raw FRED rows fetched: {len(series)} for series_id={series_id}")

    if series.empty:
        raise RuntimeError(
            f"[{output_name}] No data returned from FRED for series_id={series_id}, "
            f"start_date={start_date}, end_date={end_date}."
        )

    normalized = normalize_history(series, output_name)

    print(f"[{output_name}] Weekly Monday rows after normalization: {len(normalized)}")

    if normalized.empty:
        raise RuntimeError(
            f"[{output_name}] FRED returned data for series_id={series_id}, but no normalized weekly rows remained after processing."
        )

    return normalized


def run_fred_series(output_name: str, mode: str = "incremental") -> pd.DataFrame:
    ensure_directories()

    if output_name not in FRED_SERIES:
        raise ValueError(f"Unknown FRED output_name: {output_name}")

    series_id = FRED_SERIES[output_name]
    fallback_start = FALLBACK_START_DATES[output_name]
    output_path = OUTPUT_DIR / f"{output_name}.csv"

    existing_df = load_existing_single_value_csv(output_path, output_name)
    today = pd.Timestamp(date.today())

    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")

    if mode == "full":
        fetch_start = pd.Timestamp(fallback_start)
        print(
            f"[{output_name}] FRED mode = full. "
            f"Fetching full history from {fetch_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}."
        )
    else:
        if existing_df.empty:
            fetch_start = pd.Timestamp(fallback_start)
            print(
                f"[{output_name}] FRED mode = incremental. "
                f"No existing CSV. Using fallback start date {fetch_start.strftime('%Y-%m-%d')}."
            )
        else:
            last_record_date = pd.to_datetime(existing_df["date"], errors="coerce").max()
            fetch_start = last_record_date
            print(
                f"[{output_name}] FRED mode = incremental. "
                f"Existing last_record_date = {last_record_date.strftime('%Y-%m-%d')}. "
                f"Fetching through {today.strftime('%Y-%m-%d')}."
            )

        if not existing_df.empty and fetch_start >= today:
            print(f"[{output_name}] Existing data already reaches today. No new fetch needed.")
            return existing_df

    new_df = fetch_fred_history(
        series_id=series_id,
        output_name=output_name,
        start_date=fetch_start.strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
    )

    if new_df.empty:
        raise RuntimeError(f"[{output_name}] No rows fetched from FRED; refusing to overwrite existing CSV.")

    if mode == "full":
        final_df = merge_and_save_single_value(
            existing_df=pd.DataFrame(columns=["date", output_name]),
            new_df=new_df,
            path=output_path,
            output_name=output_name,
        )
    else:
        final_df = merge_and_save_single_value(
            existing_df=existing_df,
            new_df=new_df,
            path=output_path,
            output_name=output_name,
        )

    final_df = final_df.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)
    final_df.to_csv(output_path, index=False)

    print(f"[{output_name}] Saved weekly Monday FRED data to {output_path}")
    print(final_df.tail())
    return final_df
```

---

## 6.6 `market_collector/collectors/imir.py`

```python
import time
from datetime import date, timedelta

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from collectors.common import (
    OUTPUT_DIR,
    ERROR_DIR,
    ensure_directories,
    load_existing_multi_value_csv,
    merge_and_save_multi_value,
)


URL = "https://sbv.gov.vn/vi/l%C3%A3i-su%E1%BA%A5t-th%E1%BB%8B-tr%C6%B0%E1%BB%9Dng-li%C3%AAn-ng%C3%A2n-h%C3%A0ng"
CSV_FILE = OUTPUT_DIR / "imir.csv"
ERROR_HTML_FILE = ERROR_DIR / "imir_error.html"

mapping = {
    "Qua đêm": "overnight",
    "1 Tuần": "1w",
    "2 Tuần": "2w",
    "1 Tháng": "1m",
    "3 Tháng": "3m",
    "6 Tháng": "6m",
    "9 Tháng": "9m",
}

VALUE_COLUMNS = ["overnight", "1w", "2w", "1m", "3m", "6m", "9m"]


def save_error_html(content: str) -> None:
    ERROR_HTML_FILE.write_text(content, encoding="utf-8")


def get_driver():
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"

    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=vi-VN")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)


def fetch_current_rates() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    driver = get_driver()

    try:
        driver.get(URL)
        time.sleep(8)

        html = driver.page_source

        if "The requested URL was rejected" in html:
            save_error_html(html)
            raise RuntimeError("Request was rejected by target website")

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="new-information-view")

        if not table:
            save_error_html(html)
            raise ValueError("Table with id 'new-information-view' not found")

        tbody = table.find("tbody")
        if not tbody:
            save_error_html(html)
            raise ValueError("Table body not found")

        rates = {
            "date": today,
            "overnight": None,
            "1w": None,
            "2w": None,
            "1m": None,
            "3m": None,
            "6m": None,
            "9m": None,
        }

        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 2:
                continue

            term = tds[0].get_text(strip=True)
            rate = tds[1].get_text(strip=True).replace(",", ".")

            if term in mapping:
                rates[mapping[term]] = float(rate)

        if not any(rates[k] is not None for k in VALUE_COLUMNS):
            save_error_html(html)
            raise ValueError("No rate values were extracted from the table")

        return rates

    except Exception:
        try:
            save_error_html(driver.page_source)
        except Exception:
            pass
        raise
    finally:
        driver.quit()


def get_week_monday(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def run_imir():
    ensure_directories()

    current_rates = fetch_current_rates()
    existing_df = load_existing_multi_value_csv(CSV_FILE, VALUE_COLUMNS)

    current_date = pd.to_datetime(current_rates["date"]).date()
    monday_date = get_week_monday(current_date)

    weekly_row = {
        "date": monday_date.isoformat(),
        **{col: current_rates.get(col) for col in VALUE_COLUMNS}
    }

    new_df = pd.DataFrame([weekly_row], columns=["date"] + VALUE_COLUMNS)

    final_df = merge_and_save_multi_value(existing_df, new_df, CSV_FILE, VALUE_COLUMNS)
    final_df.to_csv(CSV_FILE, index=False)

    print(f"[imir] Saved weekly-only row for week-start Monday {weekly_row['date']} in {CSV_FILE}")
    print(weekly_row)
```

---

## 6.7 `market_collector/collectors/vn30.py`

```python
import csv
import re
import time
from datetime import date, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from collectors.common import OUTPUT_DIR, ERROR_DIR, ensure_directories


URL = "https://cafef.vn/du-lieu/lich-su-giao-dich/vn30/all-1.chn"
CSV_FILE = OUTPUT_DIR / "vn30.csv"
ERROR_HTML_FILE = ERROR_DIR / "vn30_error.html"

fieldnames = ["date", "vn30"]


def save_error_html(content: str) -> None:
    ERROR_HTML_FILE.write_text(content, encoding="utf-8")


def get_driver():
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"

    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=vi-VN")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)


def normalize_vn30_value(raw_value: str) -> str:
    value = raw_value.strip()
    value = value.replace("điểm", "").replace("Điểm", "").strip()
    value = value.replace(",", "")

    if not re.fullmatch(r"\d+(\.\d+)?", value):
        raise ValueError(f"Invalid VN30 value format: {raw_value}")

    return value


def extract_vn30_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", id="index-summary-table")
    if table:
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(" ", strip=True).upper()
                if label == "VN30INDEX":
                    value_text = cells[1].get_text(" ", strip=True)
                    return normalize_vn30_value(value_text)

    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) >= 2:
            label = cells[0].get_text(" ", strip=True).upper()
            if label == "VN30INDEX":
                value_text = cells[1].get_text(" ", strip=True)
                return normalize_vn30_value(value_text)

    text = soup.get_text("\n", strip=True)
    match = re.search(r"VN30INDEX\s+([\d,]+\.\d+)\s*điểm", text, flags=re.IGNORECASE)
    if match:
        return normalize_vn30_value(match.group(1))

    save_error_html(html)
    raise ValueError("VN30INDEX value not found in page")


def fetch_current_vn30() -> dict:
    today = date.today().strftime("%Y-%m-%d")
    driver = get_driver()

    try:
        driver.get(URL)
        time.sleep(8)

        html = driver.page_source

        if "The requested URL was rejected" in html:
            save_error_html(html)
            raise RuntimeError("Request was rejected by target website")

        vn30_value = extract_vn30_from_html(html)

        return {
            "date": today,
            "vn30": vn30_value,
        }

    except Exception:
        try:
            save_error_html(driver.page_source)
        except Exception:
            pass
        raise
    finally:
        driver.quit()


def load_existing_rows(file_path):
    rows = []

    if not file_path.exists() or file_path.stat().st_size == 0:
        return rows

    with file_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date": (row.get("date") or "").strip(),
                "vn30": (row.get("vn30") or "").strip(),
            })

    return rows


def save_rows(file_path, rows: list[dict]) -> None:
    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_week_monday(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def run_vn30():
    ensure_directories()
    current_row = fetch_current_vn30()
    rows = load_existing_rows(CSV_FILE)

    current_date = date.fromisoformat(current_row["date"])
    monday_date = get_week_monday(current_date)

    weekly_row = {
        "date": monday_date.isoformat(),
        "vn30": current_row["vn30"],
    }

    existing_index = next((i for i, row in enumerate(rows) if row["date"] == weekly_row["date"]), None)
    if existing_index is not None:
        rows[existing_index] = weekly_row
        action = "updated"
    else:
        rows.append(weekly_row)
        rows.sort(key=lambda x: x["date"])
        action = "appended"

    save_rows(CSV_FILE, rows)

    print(f"[vn30] Successfully {action} weekly-only row for week-start Monday {weekly_row['date']} in {CSV_FILE}")
    print(weekly_row)
```

---

## 6.8 `market_collector/collectors/sjc.py`

```python
import re
from datetime import date, timedelta, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup

from collectors.common import (
    OUTPUT_DIR,
    ensure_directories,
    load_existing_single_value_csv,
    merge_and_save_single_value,
    map_single_value_to_weekly_monday,
)


OUTPUT_FILE = OUTPUT_DIR / "sjc.csv"
OUTPUT_NAME = "sjc"
FALLBACK_START_DATE = "2009-01-01"

BASE_URL = "https://webgia.com/gia-vang/sjc/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SJCCollector/1.0)"
}
TIMEOUT = 30


def parse_int_number(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text or "")
    if not digits:
        raise ValueError(f"Cannot parse integer from: {text!r}")
    return int(digits)


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_sjc_sell_from_main_table(soup: BeautifulSoup) -> int:
    target_sjc = None

    tables = soup.find_all("table")
    for table in tables:
        for tr in table.select("tbody tr"):
            cells = tr.find_all(["th", "td"])
            if len(cells) < 4:
                continue

            area = cells[0].get_text(" ", strip=True)
            gold_type = cells[1].get_text(" ", strip=True)

            if area == "Hồ Chí Minh" and gold_type == "Vàng SJC 1L, 10L, 1KG":
                sell_per_chi = parse_int_number(cells[3].get_text(" ", strip=True))
                target_sjc = sell_per_chi * 10
                break
        if target_sjc is not None:
            break

    if target_sjc is None:
        raise RuntimeError("Cannot find Hồ Chí Minh / Vàng SJC 1L, 10L, 1KG row")

    return target_sjc


def extract_sjc_from_current_page() -> dict:
    soup = fetch_page(BASE_URL)

    h1 = soup.find("h1", class_="h-head")
    if not h1:
        raise RuntimeError("Cannot find page header")

    h1_text = h1.get_text(" ", strip=True)
    m = re.search(r"(\d{2}:\d{2}:\d{2})\s+(\d{2}/\d{2}/\d{4})", h1_text)
    if not m:
        raise RuntimeError("Cannot parse update datetime from current page")

    updated_date = datetime.strptime(m.group(2), "%d/%m/%Y").date()
    sjc = extract_sjc_sell_from_main_table(soup)

    return {
        "date": updated_date.isoformat(),
        OUTPUT_NAME: sjc,
    }


def extract_sjc_from_daily_page(target_date: date) -> dict:
    url = f"{BASE_URL}{target_date.strftime('%d-%m-%Y')}.html"
    soup = fetch_page(url)

    h1 = soup.find("h1", class_="h-head")
    if not h1:
        raise RuntimeError(f"Cannot find page header for {target_date.isoformat()}")

    table = soup.find("table", class_=lambda c: c and "table" in c)
    if not table:
        raise RuntimeError(f"Cannot find history table for {target_date.isoformat()}")

    data_rows = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        time_text = tds[1].get_text(" ", strip=True)
        sell_text = tds[3].get_text(" ", strip=True)

        if not re.match(r"^\d{2}:\d{2}$", time_text):
            continue

        sell_million = float(re.sub(r"[^\d.]", "", sell_text))
        sjc = int(round(sell_million * 1_000_000))
        data_rows.append((time_text, sjc))

    if not data_rows:
        raise RuntimeError(f"No daily price rows found for {target_date.isoformat()}")

    _, sjc = data_rows[-1]

    return {
        "date": target_date.isoformat(),
        OUTPUT_NAME: sjc,
    }


def fetch_sjc_incremental(existing_df: pd.DataFrame) -> pd.DataFrame:
    target_date = pd.Timestamp(date.today())
    fallback_start = pd.Timestamp(FALLBACK_START_DATE)

    print(f"[sjc] Target date: {target_date.strftime('%Y-%m-%d')}")

    if existing_df.empty:
        fetch_start_ts = fallback_start
        print(f"[sjc] No existing CSV. Starting from fallback start date: {fetch_start_ts.strftime('%Y-%m-%d')}")
    else:
        last_record_date = pd.to_datetime(existing_df["date"]).max()
        print(f"[sjc] Last record in {OUTPUT_FILE}: {last_record_date.strftime('%Y-%m-%d')}")

        if last_record_date >= target_date:
            print("[sjc] Existing data already reaches today. No new fetch needed.")
            return pd.DataFrame(columns=["date", OUTPUT_NAME])

        fetch_start_ts = last_record_date
        print(f"[sjc] Using last record date as fetch start: {fetch_start_ts.strftime('%Y-%m-%d')}")

    rows = []
    current_day = fetch_start_ts.date()
    end_day = target_date.date()

    while current_day <= end_day:
        try:
            if current_day == date.today():
                row = extract_sjc_from_current_page()
            else:
                row = extract_sjc_from_daily_page(current_day)

            rows.append({
                "date": row["date"],
                OUTPUT_NAME: row[OUTPUT_NAME],
            })
            print(f"[sjc] Fetched {row['date']} {OUTPUT_NAME}={row[OUTPUT_NAME]}")
        except Exception as e:
            print(f"[sjc] Skipped {current_day.isoformat()}: {e}")

        current_day += timedelta(days=1)

    if not rows:
        return pd.DataFrame(columns=["date", OUTPUT_NAME])

    daily_df = pd.DataFrame(rows, columns=["date", OUTPUT_NAME])
    return map_single_value_to_weekly_monday(daily_df, OUTPUT_NAME)


def run_sjc():
    ensure_directories()
    existing_df = load_existing_single_value_csv(OUTPUT_FILE, OUTPUT_NAME)
    new_df = fetch_sjc_incremental(existing_df)

    if new_df.empty and not existing_df.empty:
        print("[sjc] No changes detected. Existing file remains current.")
        print(existing_df.tail())
        return existing_df

    final_df = merge_and_save_single_value(existing_df, new_df, OUTPUT_FILE, OUTPUT_NAME)
    final_df = map_single_value_to_weekly_monday(final_df, OUTPUT_NAME)
    final_df.to_csv(OUTPUT_FILE, index=False)

    print(f"[sjc] Saved weekly Monday-based data to {OUTPUT_FILE}")
    print(final_df.tail())
    return final_df
```

---

## 6.9 `market_collector/market_collector.py`

```python
import argparse
import traceback

from collectors.imir import run_imir
from collectors.vn30 import run_vn30
from collectors.sjc import run_sjc
from collectors.fred_collector import run_fred_series, FRED_SERIES


CRAWL_TASKS = {
    "imir": run_imir,
    "vn30": run_vn30,
    "sjc": run_sjc,
}

ALL_CRAWL_TASK_NAMES = list(CRAWL_TASKS.keys())
ALL_TASK_NAMES = ALL_CRAWL_TASK_NAMES + list(FRED_SERIES.keys())


def build_parser():
    parser = argparse.ArgumentParser(description="Unified market collector")

    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all crawl collectors only: imir, vn30, sjc"
    )

    parser.add_argument(
        "--only",
        nargs="+",
        help=f"Run only selected task names. Available: {', '.join(ALL_TASK_NAMES)}"
    )

    parser.add_argument(
        "--fred-mode",
        choices=["full", "incremental"],
        default="incremental",
        help="FRED fetch mode: full history or incremental from last record date to today"
    )

    return parser


def resolve_tasks(args):
    if args.all and args.only:
        raise ValueError("Use either --all or --only, not both.")

    if args.fred_mode == "full" and args.all:
        raise ValueError(
            "--fred-mode full cannot be used with --all. "
            "Please specify exactly one FRED series with --only."
        )

    if args.all:
        selected = ALL_CRAWL_TASK_NAMES
    elif args.only:
        selected = args.only
    else:
        selected = ALL_CRAWL_TASK_NAMES

    unknown = [name for name in selected if name not in ALL_TASK_NAMES]
    if unknown:
        raise ValueError(f"Unknown task names: {unknown}")

    fred_selected = [name for name in selected if name in FRED_SERIES]

    if args.fred_mode == "full":
        if len(fred_selected) != 1:
            raise ValueError(
                "--fred-mode full requires --only with exactly one explicit FRED series."
            )

    return selected


def run_selected_tasks(task_names, fred_mode):
    success = []
    failed = []

    for name in task_names:
        print("=" * 80)
        print(f"Running task: {name}")

        try:
            if name in CRAWL_TASKS:
                CRAWL_TASKSname
            elif name in FRED_SERIES:
                run_fred_series(name, mode=fred_mode)
            else:
                raise ValueError(f"Task not configured: {name}")

            success.append(name)
            print(f"Task completed successfully: {name}")

        except Exception as e:
            failed.append(name)
            print(f"Task failed: {name}")
            print(f"Error: {e}")
            traceback.print_exc()

    print("=" * 80)
    print("Run summary")
    print(f"Successful tasks: {success}")
    print(f"Failed tasks: {failed}")


def main():
    parser = build_parser()
    args = parser.parse_args()

    selected = resolve_tasks(args)
    run_selected_tasks(selected, fred_mode=args.fred_mode)


if __name__ == "__main__":
    main()
```

---

## 6.10 `dashboard/requirements.txt`

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.6
pandas==2.2.2
plotly==5.24.1
```

---

## 6.11 `dashboard/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 6.12 `dashboard/docker-compose.yml`

```yaml
services:
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dashboard
    ports:
      - "8000:8000"
    volumes:
      - ..:/data
      - .:/app
    working_dir: /app
    restart: unless-stopped
```

---

## 6.13 `dashboard/dashboard.py`

```python
from pathlib import Path
from functools import reduce

import pandas as pd
import plotly.graph_objects as go
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse


app = FastAPI(title="Portfolio Management")

DATA_ROOT = Path("/data")
OUTPUT_DIR = DATA_ROOT / "market_collector" / "outputs"
MIN_DATE = "1971-01-01"

SERIES_FILES = {
    "gold": OUTPUT_DIR / "gold.csv",
    "sjc": OUTPUT_DIR / "sjc.csv",
    "vn30": OUTPUT_DIR / "vn30.csv",
    "us3m": OUTPUT_DIR / "us3m.csv",
    "us2y": OUTPUT_DIR / "us2y.csv",
    "us10y": OUTPUT_DIR / "us10y.csv",
    "us30y": OUTPUT_DIR / "us30y.csv",
    "dxy": OUTPUT_DIR / "dxy.csv",
    "vix": OUTPUT_DIR / "vix.csv",
    "wti": OUTPUT_DIR / "wti.csv",
    "gspc": OUTPUT_DIR / "gspc.csv",
    "stoxx": OUTPUT_DIR / "stoxx.csv",
}


def get_default_start_date():
    year = pd.Timestamp.today().year - 3
    return f"{year}-01-01"


def _empty_series_df(col_name: str) -> pd.DataFrame:
    return pd.DataFrame(columns=["date", col_name])


def _load_single_ticker_csv(file_path: Path, expected_col: str) -> pd.DataFrame:
    if not file_path.exists() or file_path.stat().st_size == 0:
        return _empty_series_df(expected_col)

    try:
        df = pd.read_csv(file_path, parse_dates=["date"])
    except Exception:
        return _empty_series_df(expected_col)

    if "date" not in df.columns or expected_col not in df.columns:
        return _empty_series_df(expected_col)

    return (
        df[["date", expected_col]]
        .copy()
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


def load_series_csv(series_name: str) -> pd.DataFrame:
    if series_name not in SERIES_FILES:
        return _empty_series_df(series_name)
    return _load_single_ticker_csv(SERIES_FILES[series_name], series_name)


def load_gold_csv():
    return load_series_csv("gold")


def load_sjc_csv():
    return load_series_csv("sjc")


def load_vn30_csv():
    return load_series_csv("vn30")


def load_csvs():
    files = []

    imir_path = OUTPUT_DIR / "imir.csv"
    if imir_path.exists() and imir_path.stat().st_size > 0:
        try:
            imir_df = pd.read_csv(imir_path, parse_dates=["date"])
            if "date" in imir_df.columns:
                imir_df = (
                    imir_df
                    .sort_values("date")
                    .drop_duplicates(subset=["date"], keep="last")
                    .reset_index(drop=True)
                )
                files.append(imir_df)
        except Exception:
            pass

    for col_name in SERIES_FILES:
        df = load_series_csv(col_name)
        if not df.empty:
            files.append(df)

    if not files:
        return pd.DataFrame(columns=["date"])

    merged_df = reduce(
        lambda left, right: pd.merge(left, right, on="date", how="outer"),
        files
    )

    return (
        merged_df
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


def filter_date_range(df, start_date=None, end_date=None):
    if df.empty or "date" not in df.columns:
        return df.copy()

    out = df.copy()
    min_date_ts = pd.to_datetime(MIN_DATE)
    out = out[out["date"] >= min_date_ts]

    if start_date:
        out = out[out["date"] >= pd.to_datetime(start_date)]

    if end_date:
        out = out[out["date"] <= pd.to_datetime(end_date)]

    return out.sort_values("date").reset_index(drop=True)


def add_yoy_columns(df):
    if df.empty or "date" not in df.columns:
        return df.copy()

    out = df.copy().sort_values("date").reset_index(drop=True)

    if "gold" in out.columns:
        out["gold_yoy_pct"] = ((out["gold"] / out["gold"].shift(52)) - 1) * 100

    if "sjc" in out.columns:
        out["sjc_yoy_pct"] = ((out["sjc"] / out["sjc"].shift(52)) - 1) * 100

    if "vn30" in out.columns:
        out["vn30_yoy_pct"] = ((out["vn30"] / out["vn30"].shift(52)) - 1) * 100

    return out


def prepare_chart_df(df):
    chart_df = df.copy()

    if "gold" in chart_df.columns:
        chart_df["gold_scaled"] = chart_df["gold"] / 1000.0

    if "gold_yoy_pct" in chart_df.columns:
        chart_df["gold_yoy_pct_scaled"] = chart_df["gold_yoy_pct"] / 10.0

    if "sjc" in chart_df.columns:
        chart_df["sjc_scaled"] = chart_df["sjc"] / 100000000.0

    if "sjc_yoy_pct" in chart_df.columns:
        chart_df["sjc_yoy_pct_scaled"] = chart_df["sjc_yoy_pct"] / 10.0

    if "vn30" in chart_df.columns:
        chart_df["vn30_scaled"] = chart_df["vn30"] / 1000.0

    if "vn30_yoy_pct" in chart_df.columns:
        chart_df["vn30_yoy_pct_scaled"] = chart_df["vn30_yoy_pct"] / 10.0

    return chart_df


def calculate_tema(series, span):
    ema1 = series.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    ema3 = ema2.ewm(span=span, adjust=False).mean()
    return (3 * ema1) - (3 * ema2) + ema3


def calculate_zscore(series, window):
    rolling_mean = series.rolling(window=window, min_periods=1).mean()
    rolling_std = series.rolling(window=window, min_periods=1).std().replace(0, pd.NA)
    return (series - rolling_mean) / rolling_std


def get_direction_score_from_delta(delta):
    if pd.isna(delta):
        return 0
    if delta > 0:
        return 1
    if delta < 0:
        return -1
    return 0


def get_direction_label_from_delta(delta):
    if pd.isna(delta):
        return "Flat"
    if delta > 0:
        return "Rising"
    if delta < 0:
        return "Falling"
    return "Flat"


def get_z_zone(z):
    if pd.isna(z):
        return "Unknown"
    if z > 2:
        return "> 2"
    if 0 <= z <= 2:
        return "0 to 2"
    if -2 <= z < 0:
        return "-2 to 0"
    return "< -2"


def get_z_zone_score(z):
    if pd.isna(z):
        return 0
    if 0 <= z <= 2:
        return 1
    if z > 2:
        return 0
    if -2 <= z < 0:
        return 0
    return -1


def get_z_direction_note(z_direction):
    if z_direction == "Rising":
        return "Momentum Improving"
    if z_direction == "Falling":
        return "Momentum Weakening"
    return "Momentum Stable"


def classify_signal(total_score):
    if total_score == 5:
        return "Strong Buy"
    if 3 <= total_score <= 4:
        return "Buy"
    if 0 <= total_score <= 2:
        return "Hold"
    if -3 <= total_score <= -1:
        return "Sell"
    return "Strong Sell"


def get_monthly_action(signal_label):
    if signal_label == "Strong Buy":
        return "Buy 1 tael each qualifying month"
    if signal_label == "Buy":
        return "Buy 1 tael once on entry into Buy zone"
    if signal_label == "Hold":
        return "Hold"
    if signal_label == "Sell":
        return "Sell 25% of current holdings"
    return "Sell 50% of current holdings"


def _prepare_indicator_df(chart_df, scaled_col, yoy_scaled_col):
    required_cols = {"date", scaled_col, yoy_scaled_col}
    if not required_cols.issubset(chart_df.columns):
        return pd.DataFrame()

    indicator_df = chart_df[["date", scaled_col, yoy_scaled_col]].copy()
    indicator_df = (
        indicator_df
        .dropna(subset=[scaled_col, yoy_scaled_col])
        .sort_values("date")
        .reset_index(drop=True)
    )

    if indicator_df.empty:
        return indicator_df

    indicator_df["ma_21"] = indicator_df[yoy_scaled_col].rolling(window=21, min_periods=1).mean()
    indicator_df["tema_55"] = calculate_tema(indicator_df[yoy_scaled_col], 55)
    indicator_df["zscore_55"] = calculate_zscore(indicator_df[yoy_scaled_col], 55)

    indicator_df["ma_21_prev"] = indicator_df["ma_21"].shift(1)
    indicator_df["tema_55_prev"] = indicator_df["tema_55"].shift(1)
    indicator_df["zscore_55_prev"] = indicator_df["zscore_55"].shift(1)

    ma21_delta = indicator_df["ma_21"] - indicator_df["ma_21_prev"]
    tema55_delta = indicator_df["tema_55"] - indicator_df["tema_55_prev"]
    z_delta = indicator_df["zscore_55"] - indicator_df["zscore_55_prev"]

    indicator_df["ma21_direction"] = ma21_delta.map(get_direction_label_from_delta)
    indicator_df["tema55_direction"] = tema55_delta.map(get_direction_label_from_delta)
    indicator_df["z_direction"] = z_delta.map(get_direction_label_from_delta)

    indicator_df["ma21_direction_score"] = ma21_delta.map(get_direction_score_from_delta)
    indicator_df["tema55_direction_score"] = tema55_delta.map(get_direction_score_from_delta)

    regime_valid = indicator_df["tema_55"].notna() & indicator_df["ma_21"].notna()
    regime_buy = regime_valid & (indicator_df["tema_55"] > indicator_df["ma_21"])
    regime_sell = regime_valid & (indicator_df["tema_55"] < indicator_df["ma_21"])

    indicator_df["regime_score"] = 0
    indicator_df.loc[regime_buy, "regime_score"] = 2
    indicator_df.loc[regime_sell, "regime_score"] = -2

    indicator_df["setup_type"] = "Neutral Regime"
    indicator_df.loc[regime_buy, "setup_type"] = "Buy Regime"
    indicator_df.loc[regime_sell, "setup_type"] = "Sell Regime"

    indicator_df["z_zone"] = indicator_df["zscore_55"].map(get_z_zone)
    indicator_df["z_zone_score"] = indicator_df["zscore_55"].map(get_z_zone_score)
    indicator_df["z_direction_note"] = indicator_df["z_direction"].map(get_z_direction_note)

    indicator_df["signal_score"] = (
        indicator_df["regime_score"]
        + indicator_df["ma21_direction_score"]
        + indicator_df["tema55_direction_score"]
        + indicator_df["z_zone_score"]
    ).clip(-5, 5)

    indicator_df["signal_label"] = indicator_df["signal_score"].map(classify_signal)
    indicator_df["monthly_action"] = indicator_df["signal_label"].map(get_monthly_action)
    indicator_df["compact_policy"] = indicator_df["monthly_action"]

    return indicator_df


def prepare_gold_yoy_indicator_df(start_date=None, end_date=None):
    gold_df = filter_date_range(load_gold_csv(), start_date, end_date)
    gold_df = add_yoy_columns(gold_df)
    chart_df = prepare_chart_df(gold_df)
    return _prepare_indicator_df(chart_df, "gold_scaled", "gold_yoy_pct_scaled")


def prepare_sjc_indicator_df(start_date=None, end_date=None):
    sjc_df = filter_date_range(load_sjc_csv(), start_date, end_date)
    sjc_df = add_yoy_columns(sjc_df)
    chart_df = prepare_chart_df(sjc_df)
    return _prepare_indicator_df(chart_df, "sjc_scaled", "sjc_yoy_pct_scaled")


def prepare_vn30_indicator_df(start_date=None, end_date=None):
    vn30_df = filter_date_range(load_vn30_csv(), start_date, end_date)
    vn30_df = add_yoy_columns(vn30_df)
    chart_df = prepare_chart_df(vn30_df)
    return _prepare_indicator_df(chart_df, "vn30_scaled", "vn30_yoy_pct_scaled")


def get_latest_signal_badge(indicator_df, label_prefix):
    if indicator_df.empty:
        return f"{label_prefix}: N/A"

    latest = indicator_df.dropna(subset=["ma_21", "tema_55", "zscore_55"]).sort_values("date", ascending=False).head(1)
    if latest.empty:
        return f"{label_prefix}: N/A"

    row = latest.iloc[0]
    return f"{label_prefix}: {row['signal_label']} ({int(row['signal_score'])})"


def build_main_chart(df):
    chart_df = prepare_chart_df(df).copy()

    preferred_visibility = {
        "vn30_scaled": True,
        "gold_scaled": True,
        "us3m": True,
    }

    excluded = {
        "date",
        "sjc",
        "gold",
        "vn30",
        "gold_yoy_pct",
        "sjc_yoy_pct",
        "vn30_yoy_pct",
        "gold_yoy_pct_scaled",
        "sjc_yoy_pct_scaled",
        "vn30_yoy_pct_scaled",
    }

    chart_columns = [
        col for col in chart_df.columns
        if col not in excluded and pd.api.types.is_numeric_dtype(chart_df[col])
    ]

    fig = go.Figure()

    for col in chart_columns:
        visible = True if preferred_visibility.get(col, False) else "legendonly"
        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df[col],
                mode="lines",
                name=col,
                visible=visible
            )
        )

    fig.update_layout(
        title="Main Dashboard - Weekly Values",
        xaxis_title="Weekly Date",
        yaxis_title="Value",
        template="plotly_dark",
        hovermode="x unified",
        height=700,
        legend_title="Tickers"
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def _build_indicator_chart(indicator_df, scaled_name, yoy_scaled_name, title):
    if indicator_df.empty:
        return f"<p>No {scaled_name} or {yoy_scaled_name} data available for indicator chart.</p>"

    customdata = indicator_df[[
        "signal_score", "signal_label", "monthly_action", "setup_type", "z_zone",
        "z_direction", "z_direction_note", "ma21_direction", "tema55_direction", "compact_policy",
    ]].values

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df[scaled_name],
        mode="lines",
        name=scaled_name,
        visible=True,
        customdata=customdata
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df[yoy_scaled_name],
        mode="lines",
        name=yoy_scaled_name,
        visible="legendonly",
        customdata=customdata
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["ma_21"],
        mode="lines",
        name="MA 21",
        line=dict(color="red"),
        visible=True,
        customdata=customdata
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["tema_55"],
        mode="lines",
        name="TEMA 55",
        line=dict(color="green"),
        visible=True,
        customdata=customdata
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["zscore_55"],
        mode="lines",
        name="Z-Score 55",
        visible=True,
        customdata=customdata
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Weekly Date",
        yaxis_title="Value",
        template="plotly_dark",
        hovermode="x unified",
        height=520,
        legend_title="Indicators",
        autosize=True,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_gold_yoy_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "gold_scaled",
        "gold_yoy_pct_scaled",
        "Gold Indicators"
    )


def build_sjc_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "sjc_scaled",
        "sjc_yoy_pct_scaled",
        "Vietnam Gold (SJC) Indicators"
    )


def build_vn30_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "vn30_scaled",
        "vn30_yoy_pct_scaled",
        "VN30 Indicators"
    )


def _build_signal_summary_html(indicator_df, scaled_name, yoy_scaled_name):
    if indicator_df.empty:
        return "<p>No signal summary available.</p>"

    latest = indicator_df.dropna(subset=["ma_21", "tema_55", "zscore_55"]).sort_values("date", ascending=False).head(1)
    if latest.empty:
        return "<p>No signal summary available.</p>"

    row = latest.iloc[0]
    summary_df = pd.DataFrame([{
        "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
        "signal_score": int(row["signal_score"]),
        "signal_label": row["signal_label"],
        "monthly_action": row["monthly_action"],
        "compact_policy": row["compact_policy"],
        scaled_name: row[scaled_name],
        yoy_scaled_name: row[yoy_scaled_name],
        "ma_21": row["ma_21"],
        "tema_55": row["tema_55"],
        "zscore_55": row["zscore_55"],
        "setup_type": row["setup_type"],
        "ma21_direction": row["ma21_direction"],
        "tema55_direction": row["tema55_direction"],
        "z_zone": row["z_zone"],
        "z_direction": row["z_direction"],
        "z_direction_note": row["z_direction_note"],
    }])
    return wrap_table_html(summary_df.to_html(index=False, border=0), height="240px")


def build_gold_signal_summary_html(indicator_df):
    return _build_signal_summary_html(
        indicator_df,
        "gold_scaled",
        "gold_yoy_pct_scaled"
    )


def build_sjc_signal_summary_html(indicator_df):
    return _build_signal_summary_html(
        indicator_df,
        "sjc_scaled",
        "sjc_yoy_pct_scaled"
    )


def build_vn30_signal_summary_html(indicator_df):
    return _build_signal_summary_html(
        indicator_df,
        "vn30_scaled",
        "vn30_yoy_pct_scaled"
    )


def build_execution_table_html():
    df = pd.DataFrame([
        {"Total Score": "5", "Signal": "Strong Buy", "Monthly Physical Gold Action": "Buy 1 tael each qualifying month"},
        {"Total Score": "3 to 4", "Signal": "Buy", "Monthly Physical Gold Action": "Buy 1 tael once on entry into Buy zone"},
        {"Total Score": "0 to 2", "Signal": "Hold", "Monthly Physical Gold Action": "Hold"},
        {"Total Score": "-1 to -3", "Signal": "Sell", "Monthly Physical Gold Action": "Sell 25% of current holdings"},
        {"Total Score": "-4 to -5", "Signal": "Strong Sell", "Monthly Physical Gold Action": "Sell 50% of current holdings"},
    ])
    return wrap_table_html(df.to_html(index=False, border=0), height="260px")


def reorder_indicator_table_columns(df):
    if df.empty:
        return df

    priority_columns = [
        "date",
        "signal_score",
        "signal_label",
        "monthly_action",
        "compact_policy",
    ]

    existing_priority = [col for col in priority_columns if col in df.columns]
    remaining = [col for col in df.columns if col not in existing_priority]

    return df[existing_priority + remaining]


def get_filtered_merged_data(start_date, end_date):
    merged_df = load_csvs()
    filtered_merged_df = filter_date_range(merged_df, start_date, end_date)
    return filtered_merged_df


def wrap_table_html(table_html, height="420px"):
    return f'<div class="table-scroll" style="max-height:{height};">{table_html}</div>'


def build_tabs(section_id, tabs):
    buttons_html = "".join([
        f'<button type="button" class="section-tab-btn {"active" if i == 0 else ""}" data-section="{section_id}" data-target="{section_id}-panel-{i}">{label}</button>'
        for i, (label, _) in enumerate(tabs)
    ])

    panels_html = "".join([
        f'<div id="{section_id}-panel-{i}" class="section-tab-panel {"active" if i == 0 else ""}">{content}</div>'
        for i, (_, content) in enumerate(tabs)
    ])

    return f"""
    <div class="section-tabs" data-section-root="{section_id}">
        <div class="section-tab-buttons">
            {buttons_html}
        </div>
        <div class="section-tab-content">
            {panels_html}
        </div>
    </div>
    """


def build_page_shell(title, body_html):
    return f"""
    <html>
    <head>
        <title>{title}</title>
        <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background: #0f1115;
                color: #e6e6e6;
            }}
            h1, h2, h3 {{
                margin-top: 0;
                color: #f5f5f5;
            }}
            table {{
                border-collapse: collapse;
                min-width: 100%;
                width: max-content;
                background: #161b22;
                color: #e6e6e6;
            }}
            th, td {{
                border: 1px solid #2d333b;
                padding: 8px;
                text-align: right;
                white-space: nowrap;
            }}
            th {{
                background-color: #1f2630;
                color: #ffffff;
                text-align: center;
                position: sticky;
                top: 0;
                z-index: 1;
            }}
            .container {{
                max-width: 1600px;
                margin: auto;
            }}
            .card {{
                background: #161b22;
                padding: 20px;
                margin-bottom: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.35);
                border: 1px solid #2d333b;
            }}
            .filter-row {{
                display: flex;
                gap: 16px;
                align-items: end;
                flex-wrap: wrap;
            }}
            .filter-item {{
                display: flex;
                flex-direction: column;
                gap: 6px;
            }}
            label {{
                color: #c9d1d9;
            }}
            input[type="date"] {{
                padding: 8px;
                border: 1px solid #3a4450;
                border-radius: 6px;
                background: #0d1117;
                color: #e6e6e6;
            }}
            button {{
                padding: 10px 16px;
                border: none;
                background: #238636;
                color: white;
                border-radius: 6px;
                cursor: pointer;
            }}
            button:hover {{
                background: #2ea043;
            }}
            .note {{
                font-size: 14px;
                color: #9da7b3;
                margin-top: 10px;
                line-height: 1.5;
            }}
            .two-col {{
                display: flex;
                gap: 20px;
                flex-wrap: wrap;
            }}
            .half {{
                flex: 1 1 700px;
                min-width: 420px;
            }}
            .table-scroll {{
                overflow: auto;
                max-width: 100%;
                border: 1px solid #2d333b;
                border-radius: 8px;
                background: #161b22;
            }}
            .plot-wrap .plotly-graph-div {{
                width: 100% !important;
            }}
            .section-title {{
                margin-bottom: 14px;
            }}
            .section-tab-buttons {{
                display: flex;
                gap: 10px;
                margin-bottom: 16px;
                flex-wrap: wrap;
            }}
            .section-tab-btn {{
                background: #30363d;
                color: #e6edf3;
            }}
            .section-tab-btn.active {{
                background: #1f6feb;
                color: white;
            }}
            .section-tab-panel {{
                display: none;
            }}
            .section-tab-panel.active {{
                display: block;
            }}
            a {{
                color: #58a6ff;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {body_html}
        </div>

        <script>
            function resizePlotsWithin(container) {{
                const plotDivs = container.querySelectorAll('.plotly-graph-div');
                plotDivs.forEach((plotDiv) => {{
                    if (window.Plotly) {{
                        Plotly.Plots.resize(plotDiv);
                    }}
                }});
            }}

            document.querySelectorAll('.section-tab-btn').forEach((btn) => {{
                btn.addEventListener('click', function() {{
                    const section = this.getAttribute('data-section');
                    const target = this.getAttribute('data-target');

                    document.querySelectorAll(`.section-tab-btn[data-section="${{section}}"]`).forEach((b) => {{
                        b.classList.remove('active');
                    }});
                    document.querySelectorAll(`[id^="${{section}}-panel-"]`).forEach((panel) => {{
                        panel.classList.remove('active');
                    }});

                    this.classList.add('active');
                    const activePanel = document.getElementById(target);
                    activePanel.classList.add('active');

                    setTimeout(() => resizePlotsWithin(activePanel), 50);
                }});
            }});

            window.addEventListener('load', function() {{
                document.querySelectorAll('.section-tab-panel.active').forEach((panel) => {{
                    resizePlotsWithin(panel);
                }});
            }});

            window.addEventListener('resize', function() {{
                document.querySelectorAll('.section-tab-panel.active').forEach((panel) => {{
                    resizePlotsWithin(panel);
                }});
            }});
        </script>
    </body>
    </html>
    """
```

---

# Part 7 — Run Instructions

## Run collector

From inside the `market_collector/` folder:

```bash
docker compose up --build
```

This default command runs:

```bash
python market_collector.py --all
```

which means:

- `imir`
- `vn30`
- `sjc`

### Run all crawl tasks manually

```bash
docker compose run --rm market-collector python market_collector.py --all
```

### Run selected crawl task

```bash
docker compose run --rm market-collector python market_collector.py --only imir
docker compose run --rm market-collector python market_collector.py --only vn30
docker compose run --rm market-collector python market_collector.py --only sjc
```

### Run FRED incremental

Run one FRED series per command if desired:

```bash
docker compose run --rm market-collector python market_collector.py --only gold --fred-mode incremental
docker compose run --rm market-collector python market_collector.py --only dxy --fred-mode incremental
docker compose run --rm market-collector python market_collector.py --only us10y --fred-mode incremental
```

### Run FRED full-history rebuild

Run one FRED series per command:

```bash
docker compose run --rm market-collector python market_collector.py --only gold --fred-mode full
docker compose run --rm market-collector python market_collector.py --only dxy --fred-mode full
docker compose run --rm market_collector.py --only wti --fred-mode full
```

### Required environment variable

Set your FRED API key before running FRED-based collection:

```bash
export FRED_API_KEY=your_fred_api_key_here
```

Or place it in a `.env` file used by Docker Compose.

---

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

# Part 8 — Notes

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
  - `gspc`
  - `stoxx`
  - `us3m`
  - `us2y`
  - `us10y`
  - `us30y`
- each dataset/series writes to its own CSV file
- each output CSV contains weekly rows
- all weekly outputs use **Monday of the week** as `date`
- FRED data is fetched using `fredapi`
- FRED observations are normalized into weekly Monday rows
- snapshot collectors `imir` and `vn30` are mapped to the week-start Monday
- `sjc` is aggregated into week-start Monday rows
- `--all` runs crawl tasks only
- FRED tasks must be run using `--only`
- `--fred-mode full` requires exactly one explicit FRED series via `--only`
- Treasury yield FRED values are used directly without Yahoo-style divide-by-10 normalization

## Dashboard notes

- dashboard reads local CSV files only
- dashboard does not fetch remote sources directly
- dashboard assumes source CSV files are already weekly
- dashboard sorts and de-duplicates rows by weekly `date` before merge
- main dashboard charts use actual weekly Monday dates on the x-axis
- main dashboard default visible tickers remain:
  - `vn30_scaled`
  - `gold_scaled`
  - `us3m`
- other series such as `dxy`, `vix`, `wti`, `gspc`, and `stoxx` are loaded into the merged table and main chart, but hidden by default
- YoY calculations use 52 weekly periods

---

# License

Personal/internal use.
