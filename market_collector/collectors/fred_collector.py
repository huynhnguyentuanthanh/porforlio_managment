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
    "dxy": "DTWEXBGS",
    "vix": "VIXCLS",
    "wti": "DCOILWTICO",
    "sp500": "SP500",
    "us3m": "DGS3MO",
    "us2y": "DGS2",
    "us10y": "DGS10",
    "us30y": "DGS30",
    "us_headline_cpi": "CPIAUCSL",
    "us_core_cpi": "CPILFESL",
    "us_real_gdp": "GDPC1",
}

FALLBACK_START_DATES = {
    "dxy": "2000-01-01",
    "vix": "1990-01-01",
    "wti": "2000-01-01",
    "sp500": "1971-01-01",
    "us3m": "1971-01-01",
    "us2y": "1971-01-01",
    "us10y": "1971-01-01",
    "us30y": "1977-01-01",
    "us_headline_cpi": "1947-01-01",
    "us_core_cpi": "1957-01-01",
    "us_real_gdp": "1947-01-01",
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
