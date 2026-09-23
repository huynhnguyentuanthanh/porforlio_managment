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
    "sp500": OUTPUT_DIR / "sp500.csv",
    "us_headline_cpi": OUTPUT_DIR / "us_headline_cpi.csv",
    "us_core_cpi": OUTPUT_DIR / "us_core_cpi.csv",
    "us_real_gdp": OUTPUT_DIR / "us_real_gdp.csv",
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

    if "dxy" in chart_df.columns:
        chart_df["dxy_scaled"] = chart_df["dxy"] / 10.0

    if "vix" in chart_df.columns:
        chart_df["vix_scaled"] = chart_df["vix"] / 10.0

    if "wti" in chart_df.columns:
        chart_df["wti_scaled"] = chart_df["wti"] / 10.0

    if "sp500" in chart_df.columns:
        chart_df["sp500_scaled"] = chart_df["sp500"] / 1000.0

    if "us_headline_cpi" in chart_df.columns:
        chart_df["us_headline_cpi_scaled"] = chart_df["us_headline_cpi"] / 100.0

    if "us_core_cpi" in chart_df.columns:
        chart_df["us_core_cpi_scaled"] = chart_df["us_core_cpi"] / 100.0

    if "us_real_gdp" in chart_df.columns:
        chart_df["us_real_gdp_scaled"] = chart_df["us_real_gdp"] / 10000.0

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
    gold_df = load_gold_csv()
    gold_df = add_yoy_columns(gold_df)
    gold_df = filter_date_range(gold_df, start_date, end_date)
    chart_df = prepare_chart_df(gold_df)
    return _prepare_indicator_df(chart_df, "gold_scaled", "gold_yoy_pct_scaled")


def prepare_sjc_indicator_df(start_date=None, end_date=None):
    sjc_df = load_sjc_csv()
    sjc_df = add_yoy_columns(sjc_df)
    sjc_df = filter_date_range(sjc_df, start_date, end_date)
    chart_df = prepare_chart_df(sjc_df)
    return _prepare_indicator_df(chart_df, "sjc_scaled", "sjc_yoy_pct_scaled")


def prepare_vn30_indicator_df(start_date=None, end_date=None):
    vn30_df = load_vn30_csv()
    vn30_df = add_yoy_columns(vn30_df)
    vn30_df = filter_date_range(vn30_df, start_date, end_date)
    chart_df = prepare_chart_df(vn30_df)
    return _prepare_indicator_df(chart_df, "vn30_scaled", "vn30_yoy_pct_scaled")


def get_latest_signal_badge(indicator_df, label_prefix):
    if indicator_df.empty:
        return f"{label_prefix}: N/A"

    latest = (
        indicator_df
        .dropna(subset=["ma_21", "tema_55", "zscore_55"])
        .sort_values("date", ascending=False)
        .head(1)
    )
    if latest.empty:
        return f"{label_prefix}: N/A"

    row = latest.iloc[0]
    return f"{label_prefix}: {row['signal_label']} ({int(row['signal_score'])})"


def build_main_chart(df):
    chart_df = prepare_chart_df(df).copy()

    main_chart_columns = [
        "vn30_scaled",
        "gold_scaled",
        "sjc_scaled",
        "us3m",
        "us2y",
        "us10y",
        "us30y",
        "dxy_scaled",
        "vix_scaled",
        "wti_scaled",
        "sp500_scaled",
        "us_headline_cpi_scaled",
        "us_core_cpi_scaled",
        "us_real_gdp_scaled",
    ]

    chart_columns = [col for col in main_chart_columns if col in chart_df.columns]

    preferred_visibility = {
        "vn30_scaled": True,
        "gold_scaled": True,
        "us3m": True,
    }

    colors = {
        "vn30_scaled": "#00E5A8",
        "gold_scaled": "#FFD166",
        "sjc_scaled": "#FF5A7A",
        "us3m": "#58A6FF",
        "us2y": "#7AA2F7",
        "us10y": "#1F6FEB",
        "us30y": "#A5B4C3",
        "dxy_scaled": "#FF7B72",
        "vix_scaled": "#FFA657",
        "wti_scaled": "#C084FC",
        "sp500_scaled": "#3FB950",
        "us_headline_cpi_scaled": "#F78166",
        "us_core_cpi_scaled": "#79C0FF",
        "us_real_gdp_scaled": "#56D364",
    }

    fig = go.Figure()

    for col in chart_columns:
        visible = True if preferred_visibility.get(col, False) else "legendonly"
        fig.add_trace(
            go.Scatter(
                x=chart_df["date"],
                y=chart_df[col],
                mode="lines",
                name=col,
                visible=visible,
                line=dict(
                    width=2,
                    color=colors.get(col, "#FFFFFF"),
                ),
                connectgaps=False,
            )
        )

    fig.update_layout(
        title="Main Dashboard - Weekly / Mixed Frequency Values",
        xaxis_title="Date",
        yaxis_title="Value",
        hovermode="x unified",
        height=700,
        legend_title="Tickers",
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e6e6e6"),
        xaxis=dict(
            gridcolor="#2d333b",
            linecolor="#8b949e",
            zerolinecolor="#2d333b",
        ),
        yaxis=dict(
            gridcolor="#2d333b",
            linecolor="#8b949e",
            zerolinecolor="#2d333b",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#2d333b",
            borderwidth=0,
        ),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def _build_indicator_chart(indicator_df, scaled_name, yoy_scaled_name, title):
    if indicator_df.empty:
        return (
            f"<p>No {scaled_name} or {yoy_scaled_name} data available for indicator chart. "
            f"Check whether the source CSV exists and whether at least 52 weeks of history "
            f"are available for YoY calculation.</p>"
        )

    customdata = indicator_df[[
        "signal_score", "signal_label", "monthly_action", "setup_type", "z_zone",
        "z_direction", "z_direction_note", "ma21_direction", "tema55_direction", "compact_policy",
    ]].values

    hovertemplate = (
        "<b>%{x|%Y-%m-%d}</b><br>"
        "Series: %{fullData.name}<br>"
        "Value: %{y:.4f}<br>"
        "Signal Score: %{customdata[0]}<br>"
        "Signal Label: %{customdata[1]}<br>"
        "Monthly Action: %{customdata[2]}<br>"
        "Setup Type: %{customdata[3]}<br>"
        "Z Zone: %{customdata[4]}<br>"
        "Z Direction: %{customdata[5]}<br>"
        "Z Note: %{customdata[6]}<br>"
        "MA21 Direction: %{customdata[7]}<br>"
        "TEMA55 Direction: %{customdata[8]}<br>"
        "Policy: %{customdata[9]}<extra></extra>"
    )

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df[scaled_name],
        mode="lines",
        name=scaled_name,
        visible=True,
        customdata=customdata,
        hovertemplate=hovertemplate,
        line=dict(width=3, color="#FFD166"),
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df[yoy_scaled_name],
        mode="lines",
        name=yoy_scaled_name,
        visible="legendonly",
        customdata=customdata,
        hovertemplate=hovertemplate,
        line=dict(width=2, color="#58A6FF"),
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["ma_21"],
        mode="lines",
        name="MA 21",
        line=dict(color="#FF4D4F", width=3),
        visible=True,
        customdata=customdata,
        hovertemplate=hovertemplate,
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["tema_55"],
        mode="lines",
        name="TEMA 55",
        line=dict(color="#00C853", width=3),
        visible=True,
        customdata=customdata,
        hovertemplate=hovertemplate,
    ))
    fig.add_trace(go.Scatter(
        x=indicator_df["date"],
        y=indicator_df["zscore_55"],
        mode="lines",
        name="Z-Score 55",
        visible=True,
        customdata=customdata,
        hovertemplate=hovertemplate,
        line=dict(color="#AB47BC", width=3),
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Weekly Date",
        yaxis_title="Value",
        hovermode="x unified",
        height=520,
        legend_title="Indicators",
        autosize=True,
        margin=dict(l=40, r=20, t=50, b=40),
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e6e6e6"),
        xaxis=dict(
            gridcolor="#2d333b",
            linecolor="#8b949e",
            zerolinecolor="#2d333b",
        ),
        yaxis=dict(
            gridcolor="#2d333b",
            linecolor="#8b949e",
            zerolinecolor="#2d333b",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#2d333b",
            borderwidth=0,
        ),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_gold_yoy_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "gold_scaled",
        "gold_yoy_pct_scaled",
        "Gold Indicators",
    )


def build_sjc_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "sjc_scaled",
        "sjc_yoy_pct_scaled",
        "Vietnam Gold (SJC) Indicators",
    )


def build_vn30_indicator_chart(indicator_df):
    return _build_indicator_chart(
        indicator_df,
        "vn30_scaled",
        "vn30_yoy_pct_scaled",
        "VN30 Indicators",
    )


def _build_signal_summary_html(indicator_df, scaled_name, yoy_scaled_name):
    if indicator_df.empty:
        return "<p>No signal summary available.</p>"

    latest = (
        indicator_df
        .dropna(subset=["ma_21", "tema_55", "zscore_55"])
        .sort_values("date", ascending=False)
        .head(1)
    )
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
        "gold_yoy_pct_scaled",
    )


def build_sjc_signal_summary_html(indicator_df):
    return _build_signal_summary_html(
        indicator_df,
        "sjc_scaled",
        "sjc_yoy_pct_scaled",
    )


def build_vn30_signal_summary_html(indicator_df):
    return _build_signal_summary_html(
        indicator_df,
        "vn30_scaled",
        "vn30_yoy_pct_scaled",
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


def add_economic_cycle_columns(df):
    if df.empty or "date" not in df.columns:
        return df.copy()

    out = df.copy().sort_values("date").reset_index(drop=True)

    if "us_real_gdp" in out.columns:
        out["us_real_gdp_growth_pct"] = (
            (out["us_real_gdp"] / out["us_real_gdp"].shift(1)) - 1
        ) * 100
        out["us_real_gdp_growth_3m_avg"] = out["us_real_gdp_growth_pct"].rolling(3, min_periods=1).mean()
        out["gdp_growth_delta"] = out["us_real_gdp_growth_3m_avg"].diff()

    if "us_headline_cpi" in out.columns:
        out["us_headline_inflation_pct"] = (
            (out["us_headline_cpi"] / out["us_headline_cpi"].shift(1)) - 1
        ) * 100
        out["us_headline_inflation_3m_avg"] = out["us_headline_inflation_pct"].rolling(3, min_periods=1).mean()
        out["headline_inflation_delta"] = out["us_headline_inflation_3m_avg"].diff()

    if "us_core_cpi" in out.columns:
        out["us_core_inflation_pct"] = (
            (out["us_core_cpi"] / out["us_core_cpi"].shift(1)) - 1
        ) * 100
        out["us_core_inflation_3m_avg"] = out["us_core_inflation_pct"].rolling(3, min_periods=1).mean()
        out["core_inflation_delta"] = out["us_core_inflation_3m_avg"].diff()

    if {"us_core_inflation_pct", "us_headline_inflation_pct"}.issubset(out.columns):
        out["core_minus_headline_inflation"] = (
            out["us_core_inflation_pct"] - out["us_headline_inflation_pct"]
        )

    if {"us_core_inflation_3m_avg", "us_headline_inflation_3m_avg"}.issubset(out.columns):
        out["core_minus_headline_inflation_3m_avg"] = (
            out["us_core_inflation_3m_avg"] - out["us_headline_inflation_3m_avg"]
        )

    if {"us10y", "us3m"}.issubset(out.columns):
        out["yield_curve_10y_3m"] = out["us10y"] - out["us3m"]

    if "yield_curve_10y_3m" not in out.columns and {"us10y", "us2y"}.issubset(out.columns):
        out["yield_curve_10y_2y"] = out["us10y"] - out["us2y"]

    return out


def _monthly_series(series_name: str, how: str = "last") -> pd.DataFrame:
    df = load_series_csv(series_name)
    if df.empty:
        return df

    temp = df.copy()
    temp["date"] = pd.to_datetime(temp["date"])
    temp = temp.sort_values("date")

    if how == "mean":
        out = (
            temp.set_index("date")
            .resample("ME")
            .mean()
            .reset_index()
        )
    else:
        out = (
            temp.set_index("date")
            .resample("ME")
            .last()
            .reset_index()
        )

    return out


def prepare_macro_monthly_df(start_date=None, end_date=None):
    headline_df = _monthly_series("us_headline_cpi", how="last")
    core_df = _monthly_series("us_core_cpi", how="last")
    gdp_df = load_series_csv("us_real_gdp")

    if headline_df.empty and core_df.empty and gdp_df.empty:
        return pd.DataFrame()

    monthly_parts = []

    if not headline_df.empty:
        monthly_parts.append(headline_df)

    if not core_df.empty:
        monthly_parts.append(core_df)

    if not gdp_df.empty:
        gdp_temp = gdp_df.copy()
        gdp_temp["date"] = pd.to_datetime(gdp_temp["date"])
        gdp_temp = gdp_temp.sort_values("date").set_index("date")

        gdp_monthly = (
            gdp_temp
            .resample("ME")
            .last()
            .ffill()
            .reset_index()
        )
        monthly_parts.append(gdp_monthly)

    if not monthly_parts:
        return pd.DataFrame()

    monthly_df = reduce(
        lambda left, right: pd.merge(left, right, on="date", how="outer"),
        monthly_parts
    ).sort_values("date").reset_index(drop=True)

    monthly_df["date"] = pd.to_datetime(monthly_df["date"])

    full_month_index = pd.date_range(
        start=monthly_df["date"].min(),
        end=monthly_df["date"].max(),
        freq="ME",
    )

    monthly_df = (
        monthly_df.set_index("date")
        .reindex(full_month_index)
        .rename_axis("date")
        .reset_index()
    )

    value_cols = [col for col in monthly_df.columns if col != "date"]
    if value_cols:
        monthly_df[value_cols] = monthly_df[value_cols].ffill()

    monthly_df = filter_date_range(monthly_df, start_date, end_date)
    return monthly_df


def get_growth_regime(gdp_growth_3m_avg, gdp_growth_delta):
    if pd.isna(gdp_growth_3m_avg):
        return "Unknown"

    if gdp_growth_3m_avg < 0:
        return "Contracting"

    if pd.notna(gdp_growth_delta) and gdp_growth_delta > 0:
        return "Accelerating"

    if pd.notna(gdp_growth_delta) and gdp_growth_delta < 0:
        return "Slowing"

    return "Stable Positive"


def get_inflation_regime(headline_3m_avg, headline_delta, core_minus_headline_3m_avg):
    if pd.isna(headline_3m_avg):
        return "Unknown"

    sticky_core = pd.notna(core_minus_headline_3m_avg) and core_minus_headline_3m_avg > 0
    headline_led = pd.notna(core_minus_headline_3m_avg) and core_minus_headline_3m_avg < 0

    if pd.notna(headline_delta) and headline_delta < 0:
        if sticky_core:
            return "Sticky Disinflation"
        return "Disinflation"

    if pd.notna(headline_delta) and headline_delta > 0:
        if headline_led:
            return "Commodity-led Reflation"
        if sticky_core:
            return "Sticky Inflation"
        return "Reflation"

    if sticky_core:
        return "Sticky Inflation"

    return "Stable Inflation"


def get_yield_curve_regime(row):
    yc_10y_3m = row.get("yield_curve_10y_3m")
    yc_10y_2y = row.get("yield_curve_10y_2y")

    chosen = yc_10y_3m if pd.notna(yc_10y_3m) else yc_10y_2y

    if pd.isna(chosen):
        return "Unknown"

    if chosen < 0:
        return "Inverted"

    if chosen < 1:
        return "Flat"

    return "Steep"


def compute_macro_score(row):
    score = 0

    gdp_growth = row.get("us_real_gdp_growth_3m_avg")
    gdp_delta = row.get("gdp_growth_delta")
    headline = row.get("us_headline_inflation_3m_avg")
    headline_delta = row.get("headline_inflation_delta")
    divergence = row.get("core_minus_headline_inflation_3m_avg")
    curve_regime = row.get("yield_curve_regime")

    if pd.notna(gdp_growth):
        if gdp_growth > 0:
            score += 1
        else:
            score -= 2

    if pd.notna(gdp_delta):
        if gdp_delta > 0:
            score += 1
        elif gdp_delta < 0:
            score -= 1

    if pd.notna(headline):
        if headline > 0:
            score += 0

    if pd.notna(headline_delta):
        if headline_delta < 0:
            score += 1
        elif headline_delta > 0:
            score -= 1

    if pd.notna(divergence):
        if divergence > 0:
            score -= 1
        elif divergence < 0:
            score += 0

    if curve_regime == "Inverted":
        score -= 2
    elif curve_regime == "Flat":
        score -= 1
    elif curve_regime == "Steep":
        score += 1

    return int(max(-5, min(5, score)))


def get_recession_warning_label(score, growth_regime, curve_regime):
    if growth_regime == "Contracting" and curve_regime == "Inverted":
        return "High Recession Risk"
    if pd.notna(score) and score <= -3:
        return "High Recession Risk"
    if pd.notna(score) and score <= -1:
        return "Moderate Recession Risk"
    return "Low Recession Risk"


def classify_economic_cycle_phase_v2(row):
    growth_regime = row.get("growth_regime")
    inflation_regime = row.get("inflation_regime")
    divergence = row.get("core_minus_headline_inflation_3m_avg")
    score = row.get("macro_score")

    if growth_regime == "Contracting":
        if "Disinflation" in str(inflation_regime):
            return "Contraction"
        return "Stagflation / Slowdown"

    if growth_regime == "Accelerating":
        if "Disinflation" in str(inflation_regime):
            return "Early Expansion"
        if "Commodity-led Reflation" in str(inflation_regime):
            return "Late Expansion"
        return "Expansion"

    if growth_regime == "Slowing":
        if pd.notna(divergence) and divergence > 0:
            return "Stagflation / Slowdown"
        if pd.notna(score) and score >= 1:
            return "Soft Landing / Mid-Cycle"
        return "Late Expansion"

    if growth_regime == "Stable Positive":
        if pd.notna(score) and score >= 2:
            return "Soft Landing / Mid-Cycle"
        if pd.notna(divergence) and divergence > 0:
            return "Stagflation / Slowdown"
        return "Expansion"

    return "Unknown"


def prepare_economic_cycle_df(start_date=None, end_date=None):
    df = prepare_macro_monthly_df(start_date, end_date)
    if df.empty:
        return pd.DataFrame()

    merged_full = get_filtered_merged_data(start_date, end_date)
    if not merged_full.empty:
        rate_cols = ["date", "us3m", "us2y", "us10y", "us30y"]
        rate_cols = [c for c in rate_cols if c in merged_full.columns]
        if rate_cols:
            rates_df = merged_full[rate_cols].copy()
            rates_df["date"] = pd.to_datetime(rates_df["date"])
            rates_df = (
                rates_df
                .set_index("date")
                .resample("ME")
                .last()
                .ffill()
                .reset_index()
            )
            df = pd.merge(df, rates_df, on="date", how="left")

    df = add_economic_cycle_columns(df)
    if df.empty:
        return pd.DataFrame()

    df["growth_regime"] = df.apply(
        lambda row: get_growth_regime(
            row.get("us_real_gdp_growth_3m_avg"),
            row.get("gdp_growth_delta"),
        ),
        axis=1,
    )

    df["inflation_regime"] = df.apply(
        lambda row: get_inflation_regime(
            row.get("us_headline_inflation_3m_avg"),
            row.get("headline_inflation_delta"),
            row.get("core_minus_headline_inflation_3m_avg"),
        ),
        axis=1,
    )

    df["yield_curve_regime"] = df.apply(get_yield_curve_regime, axis=1)
    df["macro_score"] = df.apply(compute_macro_score, axis=1)
    df["economic_cycle_phase"] = df.apply(classify_economic_cycle_phase_v2, axis=1)

    df["headline_vs_core"] = df["core_minus_headline_inflation_3m_avg"].apply(
        lambda x: "Core > Headline" if pd.notna(x) and x > 0 else
        ("Headline > Core" if pd.notna(x) and x < 0 else "Equal / N/A")
    )

    df["recession_warning"] = df.apply(
        lambda row: get_recession_warning_label(
            row.get("macro_score"),
            row.get("growth_regime"),
            row.get("yield_curve_regime"),
        ),
        axis=1,
    )

    preferred_eco_cols = [
        "date",
        "economic_cycle_phase",
        "macro_score",
        "recession_warning",
        "growth_regime",
        "inflation_regime",
        "headline_vs_core",
        "yield_curve_regime",
        "us_real_gdp_growth_3m_avg",
        "us_headline_inflation_3m_avg",
        "us_core_inflation_3m_avg",
        "core_minus_headline_inflation_3m_avg",
        "yield_curve_10y_3m",
        "yield_curve_10y_2y",
        "us_real_gdp",
        "us_headline_cpi",
        "us_core_cpi",
        "us3m",
        "us2y",
        "us10y",
        "us30y",
    ]
    existing = [c for c in preferred_eco_cols if c in df.columns]
    remaining = [c for c in df.columns if c not in existing]

    return df[existing + remaining].sort_values("date").reset_index(drop=True)


def build_economic_cycle_chart(eco_df):
    if eco_df.empty:
        return "<p>No economic cycle data available.</p>"

    custom_cols = [
        "economic_cycle_phase",
        "growth_regime",
        "inflation_regime",
        "headline_vs_core",
        "macro_score",
        "recession_warning",
        "yield_curve_regime",
    ]
    custom_cols = [c for c in custom_cols if c in eco_df.columns]
    customdata = eco_df[custom_cols].values

    def idx(col):
        return custom_cols.index(col)

    fig = go.Figure()

    if "us_real_gdp_growth_3m_avg" in eco_df.columns:
        fig.add_trace(go.Scatter(
            x=eco_df["date"],
            y=eco_df["us_real_gdp_growth_3m_avg"],
            mode="lines",
            name="GDP Growth 3M Avg %",
            line=dict(color="#00E5A8", width=3),
            customdata=customdata,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                f"Phase: %{{customdata[{idx('economic_cycle_phase')}]}}<br>"
                f"Growth Regime: %{{customdata[{idx('growth_regime')}]}}<br>"
                f"Inflation Regime: %{{customdata[{idx('inflation_regime')}]}}<br>"
                f"Headline vs Core: %{{customdata[{idx('headline_vs_core')}]}}<br>"
                f"Macro Score: %{{customdata[{idx('macro_score')}]}}<br>"
                f"Recession Warning: %{{customdata[{idx('recession_warning')}]}}<br>"
                f"Yield Curve: %{{customdata[{idx('yield_curve_regime')}]}}<br>"
                "Value: %{y:.3f}<extra></extra>"
            ),
        ))

    if "us_headline_inflation_3m_avg" in eco_df.columns:
        fig.add_trace(go.Scatter(
            x=eco_df["date"],
            y=eco_df["us_headline_inflation_3m_avg"],
            mode="lines",
            name="Headline Inflation 3M Avg %",
            line=dict(color="#FFD166", width=3),
            customdata=customdata,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                f"Phase: %{{customdata[{idx('economic_cycle_phase')}]}}<br>"
                "Value: %{y:.3f}<extra></extra>"
            ),
        ))

    if "us_core_inflation_3m_avg" in eco_df.columns:
        fig.add_trace(go.Scatter(
            x=eco_df["date"],
            y=eco_df["us_core_inflation_3m_avg"],
            mode="lines",
            name="Core Inflation 3M Avg %",
            line=dict(color="#58A6FF", width=3),
            customdata=customdata,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                f"Phase: %{{customdata[{idx('economic_cycle_phase')}]}}<br>"
                "Value: %{y:.3f}<extra></extra>"
            ),
        ))

    if "macro_score" in eco_df.columns:
        fig.add_trace(go.Scatter(
            x=eco_df["date"],
            y=eco_df["macro_score"],
            mode="lines+markers",
            name="Macro Score",
            yaxis="y2",
            line=dict(color="#FF5A7A", width=2, dash="dot"),
            customdata=customdata,
            hovertemplate=(
                "<b>%{x|%Y-%m-%d}</b><br>"
                f"Phase: %{{customdata[{idx('economic_cycle_phase')}]}}<br>"
                f"Growth Regime: %{{customdata[{idx('growth_regime')}]}}<br>"
                f"Inflation Regime: %{{customdata[{idx('inflation_regime')}]}}<br>"
                f"Headline vs Core: %{{customdata[{idx('headline_vs_core')}]}}<br>"
                f"Recession Warning: %{{customdata[{idx('recession_warning')}]}}<br>"
                f"Yield Curve: %{{customdata[{idx('yield_curve_regime')}]}}<br>"
                "Macro Score: %{y}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title="US Economic Cycle Dashboard",
        xaxis_title="Month End Date",
        yaxis=dict(
            title="Growth / Inflation %",
            gridcolor="#2d333b",
            linecolor="#8b949e",
            zerolinecolor="#2d333b",
        ),
        yaxis2=dict(
            title="Macro Score",
            overlaying="y",
            side="right",
            range=[-5.5, 5.5],
            tickmode="linear",
            dtick=1,
        ),
        hovermode="x unified",
        height=600,
        paper_bgcolor="#161b22",
        plot_bgcolor="#161b22",
        font=dict(color="#e6e6e6"),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="#2d333b",
            borderwidth=0,
        ),
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_economic_cycle_summary_html(eco_df):
    if eco_df.empty:
        return "<p>No economic cycle summary available.</p>"

    latest = eco_df.sort_values("date", ascending=False).head(1)
    if latest.empty:
        return "<p>No economic cycle summary available.</p>"

    row = latest.iloc[0]

    summary_df = pd.DataFrame([{
        "date": row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
        "economic_cycle_phase": row.get("economic_cycle_phase"),
        "macro_score": row.get("macro_score"),
        "recession_warning": row.get("recession_warning"),
        "growth_regime": row.get("growth_regime"),
        "inflation_regime": row.get("inflation_regime"),
        "headline_vs_core": row.get("headline_vs_core"),
        "yield_curve_regime": row.get("yield_curve_regime"),
        "real_gdp_growth_3m_avg_pct": row.get("us_real_gdp_growth_3m_avg"),
        "headline_inflation_3m_avg_pct": row.get("us_headline_inflation_3m_avg"),
        "core_inflation_3m_avg_pct": row.get("us_core_inflation_3m_avg"),
        "core_minus_headline_3m_avg": row.get("core_minus_headline_inflation_3m_avg"),
    }])

    return wrap_table_html(summary_df.to_html(index=False, border=0), height="260px")


def get_latest_economic_cycle_badge(eco_df):
    if eco_df.empty:
        return "Economic Cycle: N/A"

    latest = eco_df.sort_values("date", ascending=False).head(1)
    if latest.empty:
        return "Economic Cycle: N/A"

    row = latest.iloc[0]
    phase = row.get("economic_cycle_phase", "Unknown")
    score = row.get("macro_score", "N/A")
    warning = row.get("recession_warning", "N/A")
    return f"Economic Cycle: {phase} | Score: {score} | {warning}"


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
        </style>
    </head>
    <body>
        <div class="container">
            {body_html}
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home(
    start_date: str = Query(default=get_default_start_date()),
    end_date: str | None = Query(default=None),
):
    merged_df = get_filtered_merged_data(start_date, end_date)
    merged_df = add_yoy_columns(merged_df)

    main_chart_html = build_main_chart(merged_df)
    merged_table_html = wrap_table_html(
        merged_df.to_html(index=False, border=0),
        height="520px",
    )

    gold_indicator_df = reorder_indicator_table_columns(
        prepare_gold_yoy_indicator_df(start_date, end_date)
    )
    sjc_indicator_df = reorder_indicator_table_columns(
        prepare_sjc_indicator_df(start_date, end_date)
    )
    vn30_indicator_df = reorder_indicator_table_columns(
        prepare_vn30_indicator_df(start_date, end_date)
    )

    gold_chart_html = build_gold_yoy_indicator_chart(gold_indicator_df)
    sjc_chart_html = build_sjc_indicator_chart(sjc_indicator_df)
    vn30_chart_html = build_vn30_indicator_chart(vn30_indicator_df)

    gold_summary_html = build_gold_signal_summary_html(gold_indicator_df)
    sjc_summary_html = build_sjc_signal_summary_html(sjc_indicator_df)
    vn30_summary_html = build_vn30_signal_summary_html(vn30_indicator_df)

    gold_table_html = wrap_table_html(
        gold_indicator_df.to_html(index=False, border=0),
        height="420px",
    )
    sjc_table_html = wrap_table_html(
        sjc_indicator_df.to_html(index=False, border=0),
        height="420px",
    )
    vn30_table_html = wrap_table_html(
        vn30_indicator_df.to_html(index=False, border=0),
        height="420px",
    )

    execution_table_html = build_execution_table_html()

    gold_badge = get_latest_signal_badge(gold_indicator_df, "Gold")
    sjc_badge = get_latest_signal_badge(sjc_indicator_df, "SJC")
    vn30_badge = get_latest_signal_badge(vn30_indicator_df, "VN30")

    eco_df = prepare_economic_cycle_df(start_date, end_date)
    eco_chart_html = build_economic_cycle_chart(eco_df)
    eco_summary_html = build_economic_cycle_summary_html(eco_df)
    eco_table_html = wrap_table_html(
        eco_df.to_html(index=False, border=0),
        height="420px",
    )
    eco_badge = get_latest_economic_cycle_badge(eco_df)

    body_html = f"""
    <h1>Portfolio Management Dashboard</h1>

    <div class="card">
        <h2>Filters</h2>
        <form method="get" action="/">
            <div class="filter-row">
                <div class="filter-item">
                    <label for="start_date">Start date</label>
                    <input type="date" id="start_date" name="start_date" value="{start_date or ''}">
                </div>
                <div class="filter-item">
                    <label for="end_date">End date</label>
                    <input type="date" id="end_date" name="end_date" value="{end_date or ''}">
                </div>
                <div class="filter-item">
                    <button type="submit">Apply</button>
                </div>
            </div>
            <div class="note">
                Minimum allowed date is {MIN_DATE}. Default view starts from the last 3 calendar years.
            </div>
        </form>
    </div>

    <div class="card">
        <h2>Latest Signal Snapshot</h2>
        <div class="note">
            {gold_badge} &nbsp; | &nbsp; {sjc_badge} &nbsp; | &nbsp; {vn30_badge} &nbsp; | &nbsp; {eco_badge}
        </div>
    </div>

    <div class="card">
        <h2>US Economic Cycle</h2>
        <div class="two-col">
            <div class="half">
                <div class="plot-wrap">{eco_chart_html}</div>
            </div>
            <div class="half">
                <h3>Latest Economic Cycle Summary</h3>
                {eco_summary_html}
                <div class="note" style="margin-top: 16px;">
                    <b>Interpretation guide</b><br>
                    Macro Score ranges from -5 to +5.<br>
                    Higher score = better growth / easier inflation backdrop / healthier curve.<br>
                    Lower score = weaker growth / stickier inflation / worse curve structure.<br><br>

                    <b>Typical readings</b><br>
                    Early Expansion: growth improving, inflation cooling, score rising.<br>
                    Expansion: positive growth, manageable inflation, low recession risk.<br>
                    Late Expansion: growth slowing, inflation re-accelerating, score softening.<br>
                    Soft Landing / Mid-Cycle: growth positive, inflation easing, score still constructive.<br>
                    Stagflation / Slowdown: growth slowing while core inflation remains sticky.<br>
                    Contraction: negative growth and/or high recession warning.<br><br>

                    GDP remains on a monthly timeline by carrying forward the latest available GDP record.
                </div>
            </div>
        </div>
        <h3 style="margin-top:20px;">Economic Cycle Table</h3>
        {eco_table_html}
    </div>

    <div class="card">
        <h2>Main Weekly Chart</h2>
        <div class="plot-wrap">
            {main_chart_html}
        </div>
        <div class="note">
            Default visible series: vn30_scaled, gold_scaled, us3m. Other loaded series are hidden by default in the legend.
        </div>
    </div>

    <div class="card">
        <h2>Merged Weekly Dataset</h2>
        {merged_table_html}
    </div>

    <div class="card">
        <h2>Gold Indicators</h2>
        <div class="two-col">
            <div class="half">
                <div class="plot-wrap">{gold_chart_html}</div>
            </div>
            <div class="half">
                <h3>Latest Gold Signal Summary</h3>
                {gold_summary_html}
            </div>
        </div>
        <h3 style="margin-top:20px;">Gold Indicator Table</h3>
        {gold_table_html}
    </div>

    <div class="card">
        <h2>SJC Indicators</h2>
        <div class="two-col">
            <div class="half">
                <div class="plot-wrap">{sjc_chart_html}</div>
            </div>
            <div class="half">
                <h3>Latest SJC Signal Summary</h3>
                {sjc_summary_html}
            </div>
        </div>
        <h3 style="margin-top:20px;">SJC Indicator Table</h3>
        {sjc_table_html}
    </div>

    <div class="card">
        <h2>VN30 Indicators</h2>
        <div class="two-col">
            <div class="half">
                <div class="plot-wrap">{vn30_chart_html}</div>
            </div>
            <div class="half">
                <h3>Latest VN30 Signal Summary</h3>
                {vn30_summary_html}
            </div>
        </div>
        <h3 style="margin-top:20px;">VN30 Indicator Table</h3>
        {vn30_table_html}
    </div>

    <div class="card">
        <h2>Execution Policy</h2>
        {execution_table_html}
    </div>
    """

    return HTMLResponse(
        build_page_shell("Portfolio Management Dashboard", body_html)
    )
