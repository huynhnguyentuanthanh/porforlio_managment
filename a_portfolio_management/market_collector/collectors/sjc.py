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
