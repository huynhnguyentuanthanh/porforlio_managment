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
