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
