# Portfolio Management + Market Collector

A unified setup for:

1. **Market Collector**
   - one Dockerized Python 3.12 collector project
   - crawls local-market sources
   - fetches market data using `yfinance`
   - stores each dataset/ticker in its own CSV inside `outputs/`
   - each output CSV contains **weekly rows**

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

#### yfinance sources
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
│   │   ├── yfinance_collector.py
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

Each dataset/ticker is stored in its own CSV file under:

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
- `date` = weekly anchor date for that dataset

## Final weekly standard used by this project

This project uses the following weekly setup:

- `imir` uses **week-start Monday**
- `vn30` uses **week-start Monday**
- `sjc` daily values are grouped into **week-start Monday** buckets
- `yfinance` data is fetched directly from Yahoo using `interval="1wk"`
- `yfinance` weekly dates are kept **as returned by Yahoo**

### yfinance weekly standard

For yfinance series:

- data is fetched directly from Yahoo Finance using:

```python
interval="1wk"
```

- no daily-to-weekly resampling is performed
- the saved `date` is the weekly date returned by Yahoo

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

This gives a complete Monday-based weekly solution for local-market collectors.

---

# Part 4 — yfinance Mapping

| Output name | yfinance symbol |
|---|---|
| `gold` | `GC=F` |
| `dxy` | `DX-Y.NYB` |
| `vix` | `^VIX` |
| `wti` | `CL=F` |
| `gspc` | `^GSPC` |
| `stoxx` | `^STOXX50E` |
| `us3m` | `^IRX` |
| `us2y` | `^UST2Y` |
| `us10y` | `^TNX` |
| `us30y` | `^TYX` |

## Treasury normalization

Treasury yield tickers are normalized by dividing by `10`:

- `us3m`
- `us2y`
- `us10y`
- `us30y`

---

# Part 5 — Rate-Limit-Safe yfinance Operating Model

`yfinance` can trigger `YFRateLimitError` when Yahoo Finance returns HTTP 429.

This commonly happens when:
- too many requests are made in a short period
- one container or one shared enterprise IP is used by many users
- repeated debug runs hit Yahoo too often
- full-history requests are attempted for multiple tickers in one run

A common unofficial threshold is around **2,000 requests per hour per IP**, but the exact behavior is controlled by Yahoo and can vary.

## Recommended rule

For yfinance tickers, run **one ticker at a time**.

Do **not** run full-history requests for multiple yfinance tickers in a single command.

## CLI behavior used by this project

- `--all` runs **all crawl tasks only**
  - `imir`
  - `vn30`
  - `sjc`
- yfinance tasks must be run with `--only`
- only **one yfinance ticker** is allowed per run

### Recommended full-history pattern

```bash
python market_collector.py --only gold --yfinance-mode full
python market_collector.py --only dxy --yfinance-mode full
python market_collector.py --only wti --yfinance-mode full
```

### Recommended incremental pattern

```bash
python market_collector.py --only gold --yfinance-mode incremental
python market_collector.py --only dxy --yfinance-mode incremental
python market_collector.py --only wti --yfinance-mode incremental
```

## Production recommendation

- run crawl tasks together using `--all` if desired
- run yfinance tickers individually using `--only`
- optionally insert a delay between yfinance runs at the scheduler level

This reduces the chance of HTTP 429 rate limits.

---

# Part 6 — File Contents

## 6.1 `market_collector/requirements.txt`

```txt
pandas==2.2.2
requests==2.32.3
yfinance==0.2.54
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

## 6.5 `market_collector/collectors/yfinance_collector.py`

```python
from datetime import date, timedelta
import time

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFRateLimitError

from collectors.common import (
    OUTPUT_DIR,
    ensure_directories,
    load_existing_single_value_csv,
    merge_and_save_single_value,
)


YFINANCE_TICKERS = {
    "gold": "GC=F",
    "dxy": "DX-Y.NYB",
    "vix": "^VIX",
    "wti": "CL=F",
    "gspc": "^GSPC",
    "stoxx": "^STOXX50E",
    "us3m": "^IRX",
    "us2y": "^UST2Y",
    "us10y": "^TNX",
    "us30y": "^TYX",
}

YFINANCE_DIVISORS = {
    "gold": 1.0,
    "dxy": 1.0,
    "vix": 1.0,
    "wti": 1.0,
    "gspc": 1.0,
    "stoxx": 1.0,
    "us3m": 10.0,
    "us2y": 10.0,
    "us10y": 10.0,
    "us30y": 10.0,
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


def normalize_history(df: pd.DataFrame, output_name: str, divisor: float) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date", output_name])

    df = df.reset_index()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    date_col = None
    for candidate in ["Date", "Datetime"]:
        if candidate in df.columns:
            date_col = candidate
            break

    if date_col is None or "Close" not in df.columns:
        raise ValueError(f"Unexpected columns: {df.columns.tolist()}")

    dt = pd.to_datetime(df[date_col], errors="coerce")
    try:
        dt = dt.dt.tz_localize(None)
    except (TypeError, AttributeError):
        pass

    df[date_col] = dt
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

    df = df.dropna(subset=[date_col, "Close"]).sort_values(date_col)

    if divisor and divisor != 1.0:
        df["Close"] = df["Close"] / divisor

    df["date"] = df[date_col].dt.strftime("%Y-%m-%d")
    df = df[["date", "Close"]].rename(columns={"Close": output_name})
    df = df.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)

    return df


def fetch_yfinance_history(symbol: str, output_name: str, start_date: str, end_date: str, divisor: float) -> pd.DataFrame:
    yfinance_end_exclusive = (pd.Timestamp(end_date) + timedelta(days=1)).strftime("%Y-%m-%d")

    try:
        df = yf.download(
            symbol,
            start=start_date,
            end=yfinance_end_exclusive,
            interval="1wk",
            auto_adjust=False,
            progress=False,
            threads=False,
        )
    except YFRateLimitError:
        raise RuntimeError(
            f"[{output_name}] yfinance rate limited the request for symbol={symbol}. Try again later."
        )

    print(f"[{output_name}] Raw yfinance weekly rows fetched: {len(df)} for symbol={symbol}")

    if df.empty:
        raise RuntimeError(
            f"[{output_name}] No data returned from yfinance for symbol={symbol}, "
            f"start_date={start_date}, end_date={end_date}."
        )

    normalized = normalize_history(df, output_name, divisor)

    print(f"[{output_name}] Weekly rows after normalization: {len(normalized)}")

    if normalized.empty:
        raise RuntimeError(
            f"[{output_name}] yfinance returned data for symbol={symbol}, but no normalized weekly rows remained after processing."
        )

    return normalized


def run_yfinance_symbol(output_name: str, mode: str = "incremental") -> pd.DataFrame:
    ensure_directories()

    if output_name not in YFINANCE_TICKERS:
        raise ValueError(f"Unknown yfinance output_name: {output_name}")

    symbol = YFINANCE_TICKERS[output_name]
    divisor = YFINANCE_DIVISORS.get(output_name, 1.0)
    fallback_start = FALLBACK_START_DATES[output_name]
    output_path = OUTPUT_DIR / f"{output_name}.csv"

    existing_df = load_existing_single_value_csv(output_path, output_name)
    today = pd.Timestamp(date.today())

    if mode not in {"full", "incremental"}:
        raise ValueError("mode must be 'full' or 'incremental'")

    if mode == "full":
        fetch_start = pd.Timestamp(fallback_start)
        print(
            f"[{output_name}] yfinance mode = full. "
            f"Fetching full weekly history from {fetch_start.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}."
        )
    else:
        if existing_df.empty:
            fetch_start = pd.Timestamp(fallback_start)
            print(
                f"[{output_name}] yfinance mode = incremental. "
                f"No existing CSV. Using fallback start date {fetch_start.strftime('%Y-%m-%d')}."
            )
        else:
            last_record_date = pd.to_datetime(existing_df["date"], errors="coerce").max()
            fetch_start = last_record_date
            print(
                f"[{output_name}] yfinance mode = incremental. "
                f"Existing last_record_date = {last_record_date.strftime('%Y-%m-%d')}. "
                f"Fetching through {today.strftime('%Y-%m-%d')}."
            )

        if not existing_df.empty and fetch_start >= today:
            print(f"[{output_name}] Existing data already reaches today. No new fetch needed.")
            return existing_df

    new_df = fetch_yfinance_history(
        symbol=symbol,
        output_name=output_name,
        start_date=fetch_start.strftime("%Y-%m-%d"),
        end_date=today.strftime("%Y-%m-%d"),
        divisor=divisor,
    )

    if new_df.empty:
        raise RuntimeError(f"[{output_name}] No rows fetched from yfinance; refusing to overwrite existing CSV.")

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

    print(f"[{output_name}] Saved weekly Yahoo data to {output_path}")
    print(final_df.tail())
    time.sleep(5)
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
from collectors.yfinance_collector import run_yfinance_symbol, YFINANCE_TICKERS


CRAWL_TASKS = {
    "imir": run_imir,
    "vn30": run_vn30,
    "sjc": run_sjc,
}

ALL_CRAWL_TASK_NAMES = list(CRAWL_TASKS.keys())
ALL_TASK_NAMES = ALL_CRAWL_TASK_NAMES + list(YFINANCE_TICKERS.keys())


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
        "--yfinance-mode",
        choices=["full", "incremental"],
        default="incremental",
        help="yfinance fetch mode: full history or incremental from last record date to today"
    )

    return parser


def resolve_tasks(args):
    if args.all and args.only:
        raise ValueError("Use either --all or --only, not both.")

    if args.yfinance_mode == "full" and args.all:
        raise ValueError(
            "--yfinance-mode full cannot be used with --all. "
            "Please specify exactly one yfinance ticker with --only."
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

    yfinance_selected = [name for name in selected if name in YFINANCE_TICKERS]

    if len(yfinance_selected) > 1:
        raise ValueError(
            "Run yfinance tickers one at a time to reduce HTTP 429 / rate-limit risk."
        )

    if args.yfinance_mode == "full":
        if len(yfinance_selected) != 1:
            raise ValueError(
                "--yfinance-mode full requires --only with exactly one explicit yfinance ticker."
            )

    return selected


def run_selected_tasks(task_names, yfinance_mode):
    success = []
    failed = []

    for name in task_names:
        print("=" * 80)
        print(f"Running task: {name}")

        try:
            if name in CRAWL_TASKS:
                CRAWL_TASKSname
            elif name in YFINANCE_TICKERS:
                run_yfinance_symbol(name, mode=yfinance_mode)
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
    run_selected_tasks(selected, yfinance_mode=args.yfinance_mode)


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
MIN_DATE = "1971-01-01"


def get_default_start_date():
    year = pd.Timestamp.today().year - 5
    return f"{year}-01-01"


def _load_single_ticker_csv(file_path: Path, expected_col: str) -> pd.DataFrame:
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame(columns=["date", expected_col])

    df = pd.read_csv(file_path, parse_dates=["date"])
    if "date" not in df.columns or expected_col not in df.columns:
        return pd.DataFrame(columns=["date", expected_col])

    return df[["date", expected_col]].copy()


def load_csvs():
    files = []

    imir_path = DATA_ROOT / "market_collector" / "outputs" / "imir.csv"
    if imir_path.exists() and imir_path.stat().st_size > 0:
        imir_df = pd.read_csv(imir_path, parse_dates=["date"])
        if "date" in imir_df.columns:
            imir_df = imir_df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            files.append(imir_df)

    single_files = [
        ("gold", DATA_ROOT / "market_collector" / "outputs" / "gold.csv"),
        ("sjc", DATA_ROOT / "market_collector" / "outputs" / "sjc.csv"),
        ("vn30", DATA_ROOT / "market_collector" / "outputs" / "vn30.csv"),
        ("us3m", DATA_ROOT / "market_collector" / "outputs" / "us3m.csv"),
        ("us2y", DATA_ROOT / "market_collector" / "outputs" / "us2y.csv"),
        ("us10y", DATA_ROOT / "market_collector" / "outputs" / "us10y.csv"),
        ("us30y", DATA_ROOT / "market_collector" / "outputs" / "us30y.csv"),
        ("dxy", DATA_ROOT / "market_collector" / "outputs" / "dxy.csv"),
        ("vix", DATA_ROOT / "market_collector" / "outputs" / "vix.csv"),
        ("wti", DATA_ROOT / "market_collector" / "outputs" / "wti.csv"),
        ("gspc", DATA_ROOT / "market_collector" / "outputs" / "gspc.csv"),
        ("stoxx", DATA_ROOT / "market_collector" / "outputs" / "stoxx.csv"),
    ]

    for col_name, file_path in single_files:
        df = _load_single_ticker_csv(file_path, col_name)
        if not df.empty:
            df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            files.append(df)

    if not files:
        return pd.DataFrame(columns=["date"])

    merged = reduce(
        lambda left, right: pd.merge(left, right, on="date", how="outer"),
        files
    )

    merged = merged.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return merged


def load_vn30_csv():
    file_path = DATA_ROOT / "market_collector" / "outputs" / "vn30.csv"
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame(columns=["date", "vn30"])

    df = pd.read_csv(file_path, parse_dates=["date"])
    if "date" not in df.columns or "vn30" not in df.columns:
        return pd.DataFrame(columns=["date", "vn30"])

    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return df


def filter_date_range(df, start_date=None, end_date=None):
    if df.empty or "date" not in df.columns:
        return df.copy()

    df = df.copy()
    today = pd.Timestamp.today().normalize()
    min_date_ts = pd.to_datetime(MIN_DATE)

    df = df[(df["date"] >= min_date_ts) & (df["date"] <= today)]

    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]

    return df


def add_yoy_columns(df):
    weekly = df.copy().set_index("date").sort_index()

    if "gold" in weekly.columns:
        weekly["gold_yoy_pct"] = ((weekly["gold"] / weekly["gold"].shift(52)) - 1) * 100

    if "sjc" in weekly.columns:
        weekly["sjc_yoy_pct"] = ((weekly["sjc"] / weekly["sjc"].shift(52)) - 1) * 100

    if "vn30" in weekly.columns:
        weekly["vn30_yoy_pct"] = ((weekly["vn30"] / weekly["vn30"].shift(52)) - 1) * 100

    return weekly


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


def get_line_direction(current_value, prev_value):
    if pd.isna(current_value) or pd.isna(prev_value):
        return "Flat"
    if current_value > prev_value:
        return "Rising"
    if current_value < prev_value:
        return "Falling"
    return "Flat"


def get_direction_score(direction):
    if direction == "Rising":
        return 1
    if direction == "Falling":
        return -1
    return 0


def get_regime_score(tema55, ma21):
    if pd.isna(tema55) or pd.isna(ma21):
        return 0, "Neutral Regime"
    if tema55 > ma21:
        return 2, "Buy Regime"
    if tema55 < ma21:
        return -2, "Sell Regime"
    return 0, "Neutral Regime"


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


def get_z_direction(z, prev_z):
    if pd.isna(z) or pd.isna(prev_z):
        return "Flat"
    if z > prev_z:
        return "Rising"
    if z < prev_z:
        return "Falling"
    return "Flat"


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


def get_compact_policy(signal_label):
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
    required_cols = {scaled_col, yoy_scaled_col}
    if not required_cols.issubset(chart_df.columns):
        return pd.DataFrame()

    indicator_df = chart_df[[scaled_col, yoy_scaled_col]].copy()

    indicator_df["ma_21"] = indicator_df[yoy_scaled_col].rolling(window=21, min_periods=1).mean()
    indicator_df["tema_55"] = calculate_tema(indicator_df[yoy_scaled_col], 55)
    indicator_df["zscore_55"] = calculate_zscore(indicator_df[yoy_scaled_col], 55)

    indicator_df["ma_21_prev"] = indicator_df["ma_21"].shift(1)
    indicator_df["tema_55_prev"] = indicator_df["tema_55"].shift(1)
    indicator_df["zscore_55_prev"] = indicator_df["zscore_55"].shift(1)

    indicator_df["ma21_direction"] = indicator_df.apply(
        lambda row: get_line_direction(row["ma_21"], row["ma_21_prev"]),
        axis=1
    )
    indicator_df["tema55_direction"] = indicator_df.apply(
        lambda row: get_line_direction(row["tema_55"], row["tema_55_prev"]),
        axis=1
    )
    indicator_df["z_direction"] = indicator_df.apply(
        lambda row: get_z_direction(row["zscore_55"], row["zscore_55_prev"]),
        axis=1
    )

    regime_info = indicator_df.apply(
        lambda row: get_regime_score(row["tema_55"], row["ma_21"]),
        axis=1
    )
    indicator_df["regime_score"] = regime_info.apply(lambda x: x[0])
    indicator_df["setup_type"] = regime_info.apply(lambda x: x[1])

    indicator_df["ma21_direction_score"] = indicator_df["ma21_direction"].apply(get_direction_score)
    indicator_df["tema55_direction_score"] = indicator_df["tema55_direction"].apply(get_direction_score)

    indicator_df["z_zone"] = indicator_df["zscore_55"].apply(get_z_zone)
    indicator_df["z_zone_score"] = indicator_df["zscore_55"].apply(get_z_zone_score)
    indicator_df["z_direction_note"] = indicator_df["z_direction"].apply(get_z_direction_note)

    indicator_df["signal_score"] = (
        indicator_df["regime_score"]
        + indicator_df["ma21_direction_score"]
        + indicator_df["tema55_direction_score"]
        + indicator_df["z_zone_score"]
    ).clip(-5, 5)

    indicator_df["signal_label"] = indicator_df["signal_score"].apply(classify_signal)
    indicator_df["monthly_action"] = indicator_df["signal_label"].apply(get_monthly_action)
    indicator_df["compact_policy"] = indicator_df["signal_label"].apply(get_compact_policy)

    return indicator_df.reset_index()


def prepare_gold_yoy_indicator_df(df):
    chart_df = prepare_chart_df(df).copy()
    return _prepare_indicator_df(chart_df, "gold_scaled", "gold_yoy_pct_scaled")


def prepare_sjc_indicator_df(df):
    chart_df = prepare_chart_df(df).copy()
    return _prepare_indicator_df(chart_df, "sjc_scaled", "sjc_yoy_pct_scaled")


def prepare_vn30_indicator_df(df):
    chart_df = prepare_chart_df(df).copy()
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
    chart_df = prepare_chart_df(df).reset_index()

    preferred_visibility = {
        "vn30_scaled": True,
        "gold_scaled": True,
        "us3m": True,
    }

    excluded = {
        "date",
        "sjc", "gold", "gold_yoy_pct", "vn30", "vn30_yoy_pct", "sjc_yoy_pct"
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
        template="plotly_white",
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
        template="plotly_white",
        hovermode="x unified",
        height=520,
        legend_title="Indicators",
        autosize=True,
        margin=dict(l=40, r=20, t=50, b=40),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_gold_yoy_indicator_chart(df):
    return _build_indicator_chart(
        prepare_gold_yoy_indicator_df(df),
        "gold_scaled",
        "gold_yoy_pct_scaled",
        "Gold Indicators"
    )


def build_sjc_indicator_chart(df):
    return _build_indicator_chart(
        prepare_sjc_indicator_df(df),
        "sjc_scaled",
        "sjc_yoy_pct_scaled",
        "Vietnam Gold (SJC) Indicators"
    )


def build_vn30_indicator_chart(df):
    return _build_indicator_chart(
        prepare_vn30_indicator_df(df),
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


def build_gold_signal_summary_html(df):
    return _build_signal_summary_html(
        prepare_gold_yoy_indicator_df(df),
        "gold_scaled",
        "gold_yoy_pct_scaled"
    )


def build_sjc_signal_summary_html(df):
    return _build_signal_summary_html(
        prepare_sjc_indicator_df(df),
        "sjc_scaled",
        "sjc_yoy_pct_scaled"
    )


def build_vn30_signal_summary_html(df):
    return _build_signal_summary_html(
        prepare_vn30_indicator_df(df),
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


def get_filtered_weekly_data(start_date, end_date):
    df = load_csvs()
    filtered_df = filter_date_range(df, start_date, end_date)
    weekly_df = pd.DataFrame()
    if not filtered_df.empty:
        weekly_df = add_yoy_columns(filtered_df)
    return filtered_df, weekly_df


def get_filtered_vn30_weekly_data(start_date, end_date):
    df = load_vn30_csv()
    filtered_df = filter_date_range(df, start_date, end_date)
    weekly_df = pd.DataFrame()
    if not filtered_df.empty:
        weekly_df = add_yoy_columns(filtered_df)
    return filtered_df, weekly_df


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
            body {{ font-family: Arial, sans-serif; margin: 30px; background: #f8f9fa; color: #222; }}
            h1, h2, h3 {{ margin-top: 0; }}
            table {{ border-collapse: collapse; min-width: 100%; width: max-content; background: white; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; white-space: nowrap; }}
            th {{ background-color: #f2f2f2; text-align: center; position: sticky; top: 0; z-index: 1; }}
            .container {{ max-width: 1600px; margin: auto; }}
            .card {{ background: white; padding: 20px; margin-bottom: 25px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
            .filter-row {{ display: flex; gap: 16px; align-items: end; flex-wrap: wrap; }}
            .filter-item {{ display: flex; flex-direction: column; gap: 6px; }}
            input[type="date"] {{ padding: 8px; border: 1px solid #ccc; border-radius: 6px; }}
            button {{ padding: 10px 16px; border: none; background: #0d6efd; color: white; border-radius: 6px; cursor: pointer; }}
            button:hover {{ background: #0b5ed7; }}
            .note {{ font-size: 14px; color: #555; margin-top: 10px; line-height: 1.5; }}
            .two-col {{ display: flex; gap: 20px; flex-wrap: wrap; }}
            .half {{ flex: 1 1 700px; min-width: 420px; }}
            .table-scroll {{ overflow: auto; max-width: 100%; border: 1px solid #ddd; border-radius: 8px; background: white; }}
            .plot-wrap .plotly-graph-div {{ width: 100% !important; }}
            .section-title {{ margin-bottom: 14px; }}
            .section-tab-buttons {{ display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }}
            .section-tab-btn {{ background: #6c757d; }}
            .section-tab-btn.active {{ background: #198754; }}
            .section-tab-panel {{ display: none; }}
            .section-tab-panel.active {{ display: block; }}
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


@app.get("/", response_class=HTMLResponse)
def home(start_date: str | None = Query(default=None), end_date: str | None = Query(default=None)):
    effective_start_date = start_date or get_default_start_date()
    max_date = pd.Timestamp.today().strftime("%Y-%m-%d")
    end_date_value = end_date or max_date

    filtered_df, weekly_df = get_filtered_weekly_data(effective_start_date, end_date)
    _, vn30_weekly_df = get_filtered_vn30_weekly_data(effective_start_date, end_date)

    gold_indicator_df = prepare_gold_yoy_indicator_df(weekly_df) if not weekly_df.empty else pd.DataFrame()
    sjc_indicator_df = prepare_sjc_indicator_df(weekly_df) if not weekly_df.empty else pd.DataFrame()
    vn30_indicator_df = prepare_vn30_indicator_df(vn30_weekly_df) if not vn30_weekly_df.empty else pd.DataFrame()

    gold_badge = get_latest_signal_badge(gold_indicator_df, "Gold")
    sjc_badge = get_latest_signal_badge(sjc_indicator_df, "SJC")
    vn30_badge = get_latest_signal_badge(vn30_indicator_df, "VN30")

    if not filtered_df.empty:
        merged_table_df = filtered_df.sort_values("date", ascending=False)
        merged_html = wrap_table_html(merged_table_df.to_html(index=False, border=0), height="420px")
    else:
        merged_html = "<p>No merged data available for selected date range.</p>"

    if not weekly_df.empty:
        main_chart_html = build_main_chart(weekly_df)
        weekly_table_df = weekly_df.reset_index().sort_values("date", ascending=False).head(50)
        weekly_html = wrap_table_html(weekly_table_df.to_html(index=False, border=0), height="420px")
    else:
        main_chart_html = "<p>No weekly data available for selected date range.</p>"
        weekly_html = "<p>No weekly data available for selected date range.</p>"

    if not weekly_df.empty:
        gold_chart_html = build_gold_yoy_indicator_chart(weekly_df)
        gold_signal_summary_html = build_gold_signal_summary_html(weekly_df)
        gold_table_df = gold_indicator_df.sort_values("date", ascending=False).head(50)
        gold_table_df = reorder_indicator_table_columns(gold_table_df)
        gold_table_html = wrap_table_html(gold_table_df.to_html(index=False, border=0), height="360px")

        sjc_chart_html = build_sjc_indicator_chart(weekly_df)
        sjc_signal_summary_html = build_sjc_signal_summary_html(weekly_df)
        sjc_table_df = sjc_indicator_df.sort_values("date", ascending=False).head(50)
        sjc_table_df = reorder_indicator_table_columns(sjc_table_df)
        sjc_table_html = wrap_table_html(sjc_table_df.to_html(index=False, border=0), height="360px")
    else:
        gold_chart_html = "<p>No gold indicator data available for selected date range.</p>"
        gold_signal_summary_html = "<p>No signal summary available.</p>"
        gold_table_html = "<p>No gold indicator data available for selected date range.</p>"

        sjc_chart_html = "<p>No SJC indicator data available for selected date range.</p>"
        sjc_signal_summary_html = "<p>No signal summary available.</p>"
        sjc_table_html = "<p>No SJC indicator data available for selected date range.</p>"

    if not vn30_weekly_df.empty:
        vn30_chart_html = build_vn30_indicator_chart(vn30_weekly_df)
        vn30_signal_summary_html = build_vn30_signal_summary_html(vn30_weekly_df)
        vn30_table_df = vn30_indicator_df.sort_values("date", ascending=False).head(50)
        vn30_table_df = reorder_indicator_table_columns(vn30_table_df)
        vn30_table_html = wrap_table_html(vn30_table_df.to_html(index=False, border=0), height="360px")
    else:
        vn30_chart_html = "<p>No VN30 indicator data available for selected date range.</p>"
        vn30_signal_summary_html = "<p>No signal summary available.</p>"
        vn30_table_html = "<p>No VN30 indicator data available for selected date range.</p>"

    execution_table_html = build_execution_table_html()

    main_dashboard_tabs = build_tabs("main-dashboard", [
        ("Chart", f"""
            <div class="note">
                Default visible tickers are <b>vn30_scaled</b>, <b>gold_scaled</b>, and <b>us3m</b>.
                All other series are loaded but hidden by default in the legend.
                Raw <b>gold</b>, <b>gold_yoy_pct</b>, <b>sjc</b>, <b>sjc_yoy_pct</b>, <b>vn30</b>, and <b>vn30_yoy_pct</b> are excluded from the main chart.
                All source CSV files are already standardized to weekly data.
                The x-axis uses actual weekly dates, not row index positions.
                Note: yfinance weekly dates are kept as returned by Yahoo, while local snapshot-based weekly collectors use Monday anchors.
            </div>
            <div class="plot-wrap">{main_chart_html}</div>
        """),
        ("Data Tables", f"""
            <h3>Filtered Weekly Merged Data Table</h3>
            {merged_html}
            <h3 style="margin-top:20px;">Latest Weekly Data (newest 50 rows)</h3>
            {weekly_html}
        """),
    ])

    gold_tabs = build_tabs("gold-indicators", [
        ("Chart", f"""
            <div class="two-col">
                <div class="half">
                    <h3>Gold Indicators</h3>
                    <div class="plot-wrap">{gold_chart_html}</div>
                </div>
                <div class="half">
                    <h3>Vietnam Gold (SJC) Indicators</h3>
                    <div class="plot-wrap">{sjc_chart_html}</div>
                </div>
            </div>
        """),
        ("Data Tables", f"""
            <div class="two-col">
                <div class="half">
                    <h3>Latest Gold Signal Summary</h3>
                    {gold_signal_summary_html}
                    <h3 style="margin-top:20px;">Latest Gold Indicator Data (newest 50 rows)</h3>
                    {gold_table_html}
                </div>
                <div class="half">
                    <h3>Latest Vietnam Gold (SJC) Signal Summary</h3>
                    {sjc_signal_summary_html}
                    <h3 style="margin-top:20px;">Latest Vietnam Gold (SJC) Indicator Data (newest 50 rows)</h3>
                    {sjc_table_html}
                </div>
            </div>
        """),
    ])

    vn30_tabs = build_tabs("vn30-indicators", [
        ("Chart", f"""
            <div class="plot-wrap">{vn30_chart_html}</div>
        """),
        ("Data Tables", f"""
            <h3>Latest VN30 Signal Summary</h3>
            {vn30_signal_summary_html}
            <h3 style="margin-top:20px;">Latest VN30 Indicator Data (newest 50 rows)</h3>
            {vn30_table_html}
        """),
    ])

    policy_tabs = build_tabs("signal-policy", [
        ("Data Table", f"""{execution_table_html}"""),
    ])

    body_html = f"""
    <h1>Portfolio Management</h1>

    <div class="card">
        <h2 class="section-title">Section 1 — Global Filter</h2>
        <form method="get">
            <div class="filter-row">
                <div class="filter-item">
                    <label for="start_date">Start date</label>
                    <input type="date" id="start_date" name="start_date" value="{effective_start_date}" min="{MIN_DATE}" max="{max_date}">
                </div>
                <div class="filter-item">
                    <label for="end_date">End date</label>
                    <input type="date" id="end_date" name="end_date" value="{end_date_value}" min="{MIN_DATE}" max="{max_date}">
                </div>
                <div class="filter-item">
                    <button type="submit">Apply</button>
                </div>
            </div>
        </form>
        <div class="note">
            Default start date is the first day of the year from 5 years ago.
            All collector outputs are already stored as weekly data.
            Dashboard charts and tables display weekly data only.
            YoY calculations use 52 weekly periods.
            Note: weekly anchor dates may differ by source because Yahoo weekly dates are kept as returned, while local snapshot-based collectors use Monday anchors.
        </div>
    </div>

    <div class="card">
        <h2 class="section-title">Section 2 — Main Dashboard</h2>
        {main_dashboard_tabs}
    </div>

    <div class="card">
        <h2 class="section-title">Section 3 — Gold Indicators | {gold_badge} | {sjc_badge}</h2>
        {gold_tabs}
    </div>

    <div class="card">
        <h2 class="section-title">Section 4 — VN30 Indicators | {vn30_badge}</h2>
        {vn30_tabs}
    </div>

    <div class="card">
        <h2 class="section-title">Section 5 — Signal Policy Table</h2>
        {policy_tabs}
    </div>
    """

    return build_page_shell("Portfolio Management", body_html)
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

### Run yfinance incremental

Run exactly one yfinance ticker per command:

```bash
docker compose run --rm market-collector python market_collector.py --only gold --yfinance-mode incremental
docker compose run --rm market-collector python market_collector.py --only dxy --yfinance-mode incremental
docker compose run --rm market-collector python market_collector.py --only us10y --yfinance-mode incremental
```

### Run yfinance full-history rebuild

Run exactly one yfinance ticker per command:

```bash
docker compose run --rm market-collector python market_collector.py --only gold --yfinance-mode full
docker compose run --rm market-collector python market_collector.py --only dxy --yfinance-mode full
docker compose run --rm market-collector python market_collector.py --only wti --yfinance-mode full
```

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
- yfinance tasks:
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
- each dataset/ticker writes to its own CSV file
- each output CSV contains weekly rows
- yfinance data is fetched directly from Yahoo with `interval="1wk"`
- yfinance weekly dates are kept as returned by Yahoo
- snapshot collectors `imir` and `vn30` are mapped to the week-start Monday
- `sjc` is aggregated into week-start Monday rows
- `--all` runs crawl tasks only
- yfinance tasks must be run using `--only`
- yfinance runs are intentionally restricted to one ticker per run to reduce HTTP 429 risk
- `--yfinance-mode full` requires exactly one explicit yfinance ticker via `--only`
- Treasury yield yfinance values are normalized by dividing by `10`

## Dashboard notes

- dashboard reads local CSV files only
- dashboard does not fetch remote sources directly
- dashboard assumes source CSV files are already weekly
- dashboard sorts and de-duplicates rows by weekly `date` before merge
- main dashboard charts use actual weekly dates on the x-axis
- main dashboard default visible tickers remain:
  - `vn30_scaled`
  - `gold_scaled`
  - `us3m`
- other series such as `dxy`, `vix`, `wti`, `gspc`, and `stoxx` are loaded into the merged table and main chart, but hidden by default
- because this design keeps Yahoo weekly dates as returned, date alignment may differ slightly from Monday-anchored local-market series

---

# Part 9 — Troubleshooting

## yfinance rate limit error

If you see `YFRateLimitError` or HTTP 429:

- wait before retrying
- run only one yfinance ticker at a time
- avoid repeated debug loops against Yahoo
- avoid multi-ticker full-history runs

## Collector full yfinance mode error

If you see a validation error for full mode, check that:

- you used `--only`
- exactly one yfinance ticker is explicitly listed
- you did not use `--all --yfinance-mode full`

## `--all` does not run yfinance

This is expected.

The project intentionally defines:

- `--all` = all crawl tasks only
- yfinance = one ticker per run via `--only`

This is done to reduce Yahoo Finance HTTP 429 rate-limit risk.

## Dashboard cannot find files

Check the dashboard compose mount:

```yaml
volumes:
  - ..:/data
  - .:/app
```

This allows the dashboard container to read:

- `/data/market_collector/outputs/*.csv`

## Empty chart

Possible causes:

- CSV files are empty or missing
- selected date range contains no data
- fewer than 52 weekly rows exist for YoY calculations
- source collectors have not run recently

## Treasury yields look too large

This unified collector divides these yfinance series by `10`:

- `us3m`
- `us2y`
- `us10y`
- `us30y`

If values still look off, verify the ticker conventions in your runtime environment.

## IMIR or VN30 weekly row changes during the week

This is expected.

IMIR and VN30 are snapshot-based collectors. If you run the collector multiple times during the same week, the current week’s Monday row will be overwritten with the latest available snapshot.

That means:
- Monday through Sunday runs produce the same week-start Monday anchor
- repeated runs during the same week update that same Monday row

## SJC weekly row behavior

SJC is built from daily observations and then grouped into Monday-based weeks.

That means:
- multiple daily observations in the same week roll into one Monday-anchored weekly bucket
- the last available daily observation in that week is kept

## Chart x-axis looks wrong

If charts do not appear to show weekly dates correctly, verify that:

- source CSV files contain a `date` column
- the `date` column is parsed as datetime
- the dashboard is using `x=...["date"]` rather than dataframe index positions
- the source collector outputs remain weekly
- date alignment may vary slightly because Yahoo weekly dates are kept as-is while local-market collectors use Monday anchors

---

# License

Personal/internal use.
