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
