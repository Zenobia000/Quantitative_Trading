"""Sprint 0 Spike S6 — Streamlit + TimescaleDB equity curve POC.

Validates:
1. Streamlit launches
2. Connects to TimescaleDB
3. Reads equity_snapshots (seeded by s6_seed_equity_data.py)
4. Renders interactive plotly equity curve + drawdown
5. Page loads in < 2 seconds

Run AFTER s6_seed_equity_data.py:
    uv run streamlit run sprint_0_spikes/s6_streamlit_dashboard.py

Pass criteria: page opens at http://localhost:8501, equity curve visible.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]


@st.cache_resource
def get_engine():
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv(ROOT / ".env")
    url = (
        f"postgresql+psycopg2://{os.environ.get('POSTGRES_USER', 'quant')}:"
        f"{os.environ.get('POSTGRES_PASSWORD', 'change_me_in_production')}@"
        f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
        f"{os.environ.get('POSTGRES_PORT', '5432')}/"
        f"{os.environ.get('POSTGRES_DB', 'quant_trading')}"
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=60)
def load_equity(strategy_id: str) -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT snapshot_time, equity, cash, positions_value, open_positions, drawdown
        FROM equity_snapshots
        WHERE strategy_id = %(sid)s
        ORDER BY snapshot_time
    """
    return pd.read_sql(query, engine, params={"sid": strategy_id})


def render(df: pd.DataFrame):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.05,
        subplot_titles=("Equity Curve", "Drawdown"),
    )
    fig.add_trace(
        go.Scatter(
            x=df["snapshot_time"], y=df["equity"], name="Equity",
            line=dict(color="#1f77b4", width=2),
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=df["snapshot_time"], y=df["drawdown"] * 100, name="DD %",
            fill="tozeroy", line=dict(color="#d62728"),
        ),
        row=2, col=1,
    )
    fig.update_layout(
        height=600,
        showlegend=True,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="Equity (NTD)", row=1, col=1)
    fig.update_yaxes(title_text="Drawdown %", row=2, col=1)
    return fig


def main():
    st.set_page_config(
        page_title="Sprint 0 Spike S6 — Equity Dashboard POC",
        layout="wide",
    )
    st.title("Equity Dashboard POC")
    st.caption("Sprint 0 Spike S6 — validates Streamlit + TimescaleDB + plotly stack")

    strategy_id = st.selectbox(
        "Strategy", ["four_layer_resonance_v2.1"], index=0
    )

    t0 = time.perf_counter()
    try:
        df = load_equity(strategy_id)
    except Exception as e:
        st.error(f"DB load failed: {e}")
        st.info("Run `uv run python sprint_0_spikes/s6_seed_equity_data.py` first.")
        return
    load_ms = (time.perf_counter() - t0) * 1000

    if df.empty:
        st.warning("No data. Run s6_seed_equity_data.py to seed synthetic data.")
        return

    col1, col2, col3, col4 = st.columns(4)
    init_eq = float(df["equity"].iloc[0])
    final_eq = float(df["equity"].iloc[-1])
    total_ret = (final_eq - init_eq) / init_eq
    max_dd = float(df["drawdown"].min())

    col1.metric("Initial Equity", f"NT$ {init_eq:,.0f}")
    col2.metric("Current Equity", f"NT$ {final_eq:,.0f}", f"{total_ret:.2%}")
    col3.metric("Max Drawdown", f"{max_dd:.2%}")
    col4.metric("DB load latency", f"{load_ms:.0f} ms",
                "✅ < 100ms" if load_ms < 100 else "⚠️ > 100ms")

    st.plotly_chart(render(df), use_container_width=True)

    with st.expander("Raw data (last 20 rows)"):
        st.dataframe(df.tail(20))

    st.success(
        f"[S6] Dashboard loaded successfully ({len(df)} rows in {load_ms:.0f}ms)"
    )


if __name__ == "__main__":
    main()
