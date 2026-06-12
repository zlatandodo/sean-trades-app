"""
Sean Trades Weekly Scanner — Streamlit Dashboard
=================================================
Interactive dashboard emulating the "Back to Basics" method by Sean Trades.

Run locally:   streamlit run app.py
Deploy:        Streamlit Community Cloud (see DEPLOY.md)

Tabs:
  1. Overview  — market context, leading sectors, 3-level funnel
  2. Setups    — filterable / sortable table of all setups
  3. Chart     — TradingView-style candlestick + EMA + volume per ticker
  4. History   — browse past weekly scans
"""

import os
import glob
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

# Project imports
from tools.scanner_sean_trades import run_scan
from tools.technical_analysis import SetupScore

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sean Trades Scanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp")

GRADE_COLORS = {"A+": "#0a7d2e", "A": "#1a9e4b", "B": "#c98a00", "C": "#888", "F": "#bbb"}


# ── Data helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def run_full_scan(min_grade: str):
    """Run the scanner and return results as a DataFrame + metadata. Cached 1h."""
    scan = run_scan(min_grade=min_grade)
    rows = []
    for r in scan["results"]:
        rows.append({
            "Ticker": r.ticker, "Sector": r.sector, "Industry": r.industry,
            "Grade": r.grade, "Score": round(r.total_score, 1), "Price": r.price,
            "EMA8": r.ema8, "EMA21": r.ema21, "EMA50": r.ema50,
            "Compression": r.compression_ratio, "VolPattern": r.volume_pattern,
            "Candle": r.last_candle_pattern, "NearBreakout": r.near_breakout,
            "Signals": " | ".join(r.signals),
        })
    df = pd.DataFrame(rows)
    return df, scan


@st.cache_data(ttl=900, show_spinner=False)
def load_chart_data(ticker: str):
    """Download 6mo daily OHLCV for a ticker. Cached 15m."""
    data = yf.download(ticker, period="6mo", interval="1d",
                       progress=False, auto_adjust=True)
    if data is None or data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    for span in (8, 21, 50):
        data[f"EMA{span}"] = data["Close"].ewm(span=span, adjust=False).mean()
    data["VolMA20"] = data["Volume"].rolling(20).mean()
    return data


def list_history_files():
    """Return sorted list of past scan CSVs (newest first)."""
    files = glob.glob(os.path.join(TMP_DIR, "scan_results_*.csv"))
    return sorted(files, reverse=True)


def grade_badge(grade: str) -> str:
    color = GRADE_COLORS.get(grade, "#888")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{grade}</span>'


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("📊 Sean Trades Scanner")
st.sidebar.caption('Metodo "Back to Basics" — @SRxTrades')

min_grade = st.sidebar.selectbox(
    "Grado minimo", ["A+", "A", "B", "C"], index=2,
    help="Soglia minima di qualità del setup da mostrare",
)

if st.sidebar.button("🔄 Esegui nuovo scan", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    "**Imbuto a 3 livelli:**\n\n"
    "1. Settore (top 3 momentum)\n"
    "2. Industria (top 3 nel settore)\n"
    "3. Leaders (titoli filtrati)\n\n"
    "**Scoring /16:** trend mercato · EMA stack · "
    "compressione · volume pattern · candele · breakout"
)
st.sidebar.divider()
st.sidebar.caption("⚠️ Non è un consiglio finanziario. "
                   "Conferma sempre i setup manualmente.")


# ── Run scan (cached) ────────────────────────────────────────────────────────
with st.spinner("🔬 Scansione del mercato in corso (settori → industrie → titoli)..."):
    df, scan = run_full_scan(min_grade)

market_bull = scan["market_bull"]
sectors = scan["sectors"]
funnel = scan["funnel"]


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_overview, tab_setups, tab_chart, tab_history = st.tabs(
    ["🏠 Overview", "🎯 Setups", "📈 Chart", "🗂️ Storico"]
)

# ── TAB 1: Overview ──────────────────────────────────────────────────────────
with tab_overview:
    st.header("Panoramica settimanale")
    st.caption(f"Scan del {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stato mercato", "BULLISH ✅" if market_bull else "DEBOLE ⚠️")
    c2.metric("Setup trovati", len(df))
    c3.metric("Grade A+/A", int((df["Grade"].isin(["A+", "A"])).sum()) if not df.empty else 0)
    top_pick = df.iloc[0]["Ticker"] if not df.empty else "—"
    c4.metric("Top pick", top_pick)

    if not market_bull:
        st.warning("Il mercato non è in chiaro uptrend (SPY/QQQ). "
                   "Il metodo di Sean consiglia cautela: solo setup A+ e size ridotta.")

    st.divider()
    st.subheader("🔻 Imbuto: Settore → Industria → Leaders")

    if funnel:
        for f in funnel:
            sec_score = next((s["score"] for s in sectors if s["sector"] == f["sector"]), 0)
            with st.expander(f"**{f['sector']}**  (score {sec_score:+.2f}) — {f['n_tickers']} titoli", expanded=True):
                ind_cols = st.columns(len(f["top_industries"]) or 1)
                for col, ti in zip(ind_cols, f["top_industries"]):
                    col.metric(ti["industry"], f"{ti['score']:+.2f}")
                # Tickers in this sector
                sec_df = df[df["Sector"] == f["sector"]]
                if not sec_df.empty:
                    chips = "  ".join(
                        f"`{row.Ticker}` {row.Grade}" for row in sec_df.itertuples()
                    )
                    st.markdown(chips)
    else:
        st.info("Dati funnel non disponibili in questo scan.")

# ── TAB 2: Setups ────────────────────────────────────────────────────────────
with tab_setups:
    st.header("🎯 Tutti i setup")

    if df.empty:
        st.info("Nessun setup ha raggiunto la soglia di grado selezionata.")
    else:
        fc1, fc2, fc3 = st.columns(3)
        sectors_avail = ["Tutti"] + sorted(df["Sector"].unique().tolist())
        sel_sector = fc1.selectbox("Settore", sectors_avail)
        sel_grade = fc2.multiselect("Grade", sorted(df["Grade"].unique()),
                                     default=sorted(df["Grade"].unique()))
        only_bo = fc3.checkbox("Solo near-breakout ⚡", value=False)

        view = df.copy()
        if sel_sector != "Tutti":
            view = view[view["Sector"] == sel_sector]
        if sel_grade:
            view = view[view["Grade"].isin(sel_grade)]
        if only_bo:
            view = view[view["NearBreakout"]]

        st.caption(f"{len(view)} setup mostrati")
        st.dataframe(
            view[["Ticker", "Sector", "Industry", "Grade", "Score", "Price",
                  "VolPattern", "Candle", "NearBreakout"]],
            use_container_width=True, hide_index=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=16, format="%.1f"),
                "NearBreakout": st.column_config.CheckboxColumn("⚡ BO"),
                "Price": st.column_config.NumberColumn("Prezzo", format="$%.2f"),
            },
        )

        csv = view.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Scarica CSV", csv,
                           f"scan_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

# ── TAB 3: Chart ─────────────────────────────────────────────────────────────
with tab_chart:
    st.header("📈 Grafico setup")

    if df.empty:
        st.info("Nessun titolo da visualizzare.")
    else:
        sel = st.selectbox("Seleziona ticker", df["Ticker"].tolist())
        row = df[df["Ticker"] == sel].iloc[0]

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Grade", row["Grade"])
        m2.metric("Score", f"{row['Score']}/16")
        m3.metric("Prezzo", f"${row['Price']:.2f}")
        m4.metric("Volume", row["VolPattern"])
        m5.metric("Candela", row["Candle"])

        data = load_chart_data(sel)
        if data is None:
            st.error("Dati grafico non disponibili.")
        else:
            fig = make_subplots(
                rows=2, cols=1, shared_xaxes=True,
                row_heights=[0.75, 0.25], vertical_spacing=0.03,
            )
            # Candlestick
            fig.add_trace(go.Candlestick(
                x=data.index, open=data["Open"], high=data["High"],
                low=data["Low"], close=data["Close"], name="Prezzo",
                increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
            ), row=1, col=1)
            # EMAs
            for span, color in [(8, "#2196f3"), (21, "#ff9800"), (50, "#9c27b0")]:
                fig.add_trace(go.Scatter(
                    x=data.index, y=data[f"EMA{span}"], name=f"EMA{span}",
                    line=dict(color=color, width=1.2),
                ), row=1, col=1)
            # Volume
            vol_colors = ["#26a69a" if c >= o else "#ef5350"
                          for c, o in zip(data["Close"], data["Open"])]
            fig.add_trace(go.Bar(
                x=data.index, y=data["Volume"], name="Volume",
                marker_color=vol_colors, opacity=0.6,
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=data.index, y=data["VolMA20"], name="Vol MA20",
                line=dict(color="#888", width=1),
            ), row=2, col=1)

            fig.update_layout(
                height=620, xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", y=1.02, yanchor="bottom"),
                margin=dict(l=10, r=10, t=30, b=10),
                template="plotly_white",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Segnali rilevati")
            for sig in str(row["Signals"]).split(" | "):
                if sig:
                    st.markdown(f"- ✅ {sig}")

# ── TAB 4: History ───────────────────────────────────────────────────────────
with tab_history:
    st.header("🗂️ Storico scan")
    files = list_history_files()
    if not files:
        st.info("Nessuno scan storico salvato ancora.")
    else:
        labels = [os.path.basename(f).replace("scan_results_", "").replace(".csv", "")
                  for f in files]
        sel_file = st.selectbox("Data scan (YYYYMMDD)", labels)
        path = os.path.join(TMP_DIR, f"scan_results_{sel_file}.csv")
        if os.path.exists(path):
            hdf = pd.read_csv(path)
            st.caption(f"{len(hdf)} setup salvati il {sel_file}")
            cols = [c for c in ["Ticker", "Sector", "Industry", "Grade", "Score",
                                "Price", "VolPattern", "CandlePattern", "NearBreakout"]
                    if c in hdf.columns]
            st.dataframe(hdf[cols], use_container_width=True, hide_index=True)
