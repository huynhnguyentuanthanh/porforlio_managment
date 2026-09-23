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
