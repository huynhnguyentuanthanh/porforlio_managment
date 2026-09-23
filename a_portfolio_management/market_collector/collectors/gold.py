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


OUTPUT_FILE = OUTPUT_DIR / "gold.csv"
OUTPUT_NAME = "gold"
FALLBACK_START_DATE = "2009-01-01"

BASE_URL = "https://giavang.org/the-gioi/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GoldCollector/1.0)"
}
TIMEOUT = 30


def parse_float_number(text: str) -> float:
    cleaned = re.sub(r"[^\d.,]", "", text or "").replace(",", "")
    if not cleaned:
        raise ValueError(f"Cannot parse float from: {text!r}")
    return float(cleaned)


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_gold_from_current_page() -> dict:
    soup = fetch_page(BASE_URL)

    h1 = soup.find("h1", class_="box-headline")
    if not h1:
        raise RuntimeError("Cannot find page header")

    h1_text = h1.get_text(" ", strip=True)
    m = re.search(r"(\d{2}:\d{2}:\d{2})\s+(\d{2}/\d{2}/\d{4})", h1_text)
    if not m:
        raise RuntimeError("Cannot parse update datetime from current page")

    updated_date = datetime.strptime(m.group(2), "%d/%m/%Y").date()

    price_span = soup.find("span", class_="crypto-price")
    if not price_span:
        raise RuntimeError("Cannot find gold price span")

    gold = parse_float_number(price_span.get_text(" ", strip=True))

    return {
        "date": updated_date.isoformat(),
        OUTPUT_NAME: gold,
    }


def extract_gold_from_daily_page(target_date: date) -> dict:
    url = f"{BASE_URL}{target_date.strftime('%d-%m-%Y')}.html"
    soup = fetch_page(url)

    h1 = soup.find("h1", class_="box-headline")
    if not h1:
        raise RuntimeError(f"Cannot find page header for {target_date.isoformat()}")

    price_span = soup.find("span", class_="crypto-price")
    if not price_span:
        raise RuntimeError(f"Cannot find gold price span for {target_date.isoformat()}")

    gold = parse_float_number(price_span.get_text(" ", strip=True))

    return {
        "date": target_date.isoformat(),
        OUTPUT_NAME: gold,
    }


def fetch_gold_incremental(existing_df: pd.DataFrame) -> pd.DataFrame:
    target_date = pd.Timestamp(date.today())
    fallback_start = pd.Timestamp(FALLBACK_START_DATE)

    print(f"[gold] Target date: {target_date.strftime('%Y-%m-%d')}")

    if existing_df.empty:
        fetch_start_ts = fallback_start
        print(f"[gold] No existing CSV. Starting from fallback start date: {fetch_start_ts.strftime('%Y-%m-%d')}")
    else:
        last_record_date = pd.to_datetime(existing_df["date"]).max()
        print(f"[gold] Last record in {OUTPUT_FILE}: {last_record_date.strftime('%Y-%m-%d')}")

        if last_record_date >= target_date:
            print("[gold] Existing data already reaches today. No new fetch needed.")
            return pd.DataFrame(columns=["date", OUTPUT_NAME])

        fetch_start_ts = last_record_date
        print(f"[gold] Using last record date as fetch start: {fetch_start_ts.strftime('%Y-%m-%d')}")

    rows = []
    current_day = fetch_start_ts.date()
    end_day = target_date.date()

    while current_day <= end_day:
        try:
            if current_day == date.today():
                row = extract_gold_from_current_page()
            else:
                row = extract_gold_from_daily_page(current_day)

            rows.append({
                "date": row["date"],
                OUTPUT_NAME: row[OUTPUT_NAME],
            })
            print(f"[gold] Fetched {row['date']} {OUTPUT_NAME}={row[OUTPUT_NAME]}")
        except Exception as e:
            print(f"[gold] Skipped {current_day.isoformat()}: {e}")

        current_day += timedelta(days=1)

    if not rows:
        return pd.DataFrame(columns=["date", OUTPUT_NAME])

    daily_df = pd.DataFrame(rows, columns=["date", OUTPUT_NAME])
    return map_single_value_to_weekly_monday(daily_df, OUTPUT_NAME)


def run_gold():
    ensure_directories()
    existing_df = load_existing_single_value_csv(OUTPUT_FILE, OUTPUT_NAME)
    new_df = fetch_gold_incremental(existing_df)

    if new_df.empty and not existing_df.empty:
        print("[gold] No changes detected. Existing file remains current.")
        print(existing_df.tail())
        return existing_df

    final_df = merge_and_save_single_value(existing_df, new_df, OUTPUT_FILE, OUTPUT_NAME)
    final_df = map_single_value_to_weekly_monday(final_df, OUTPUT_NAME)
    final_df.to_csv(OUTPUT_FILE, index=False)

    print(f"[gold] Saved weekly Monday-based data to {OUTPUT_FILE}")
    print(final_df.tail())
    return final_df
