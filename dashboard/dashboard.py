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
