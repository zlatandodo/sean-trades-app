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
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

# Project imports
from tools.scanner_sean_trades import run_scan
from tools.technical_analysis import SetupScore
from tools.finviz_sectors import get_all_sectors_ranked, WEIGHTS
from tools.stock_screener import build_filters, FILTER_OPTIONS

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sean Scanner",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tmp")

GRADE_COLORS = {"A+": "#0a7d2e", "A": "#1a9e4b", "B": "#c98a00", "C": "#888", "F": "#bbb"}


# ── Data helpers ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def run_full_scan(min_grade: str, weights_key: tuple, top_n: int,
                  max_per_sector: int, filters_key: tuple):
    """
    Run the scanner and return results as a DataFrame + metadata. Cached 1h.
    weights_key / filters_key are hashable tuples so the cache reflects params.
    """
    weights = dict(weights_key)
    mc, pr, av, rv = filters_key
    base_filters = build_filters(mc, pr, av, rv)
    scan = run_scan(min_grade=min_grade, weights=weights, top_n_sectors=top_n,
                    max_per_sector=max_per_sector, base_filters=base_filters)
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


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_sectors(weights_key: tuple):
    """All sectors with the full Relative Strength breakdown. Cached 1h."""
    return get_all_sectors_ranked(dict(weights_key))


def tradingview_url(ticker: str) -> str:
    """Public TradingView symbol page for a ticker."""
    return f"https://www.tradingview.com/symbols/{ticker}/"


@st.cache_data(ttl=86400, show_spinner=False)
def get_business_description(ticker: str, max_len: int = 240) -> str:
    """
    Short business description for a ticker (from Yahoo Finance).
    Truncated to ~max_len chars at a sentence/word boundary. Cached 24h.
    """
    try:
        info = yf.Ticker(ticker).info
        summary = (info or {}).get("longBusinessSummary", "") or ""
    except Exception:
        summary = ""
    summary = summary.strip()
    if not summary:
        return ""
    if len(summary) <= max_len:
        return summary
    cut = summary[:max_len]
    # prefer cutting at the last sentence end, else last space
    dot = cut.rfind(". ")
    if dot > 60:
        return cut[:dot + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(",;: ") + "…"


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


def tradingview_widget_html(ticker: str, height: int = 360) -> str:
    """
    Return an embeddable TradingView Advanced Chart widget for a ticker.
    Daily timeframe, EMA 8/21/50 overlays, volume — TradingView-plugin style
    (like asklivermore.com). Renders as a self-contained iframe.
    """
    container_id = f"tv_{ticker.replace('.', '_').replace('-', '_')}"
    return f"""
    <div class="tradingview-widget-container" style="height:{height}px">
      <div id="{container_id}" style="height:{height}px"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{ticker}",
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "it",
        "hide_top_toolbar": true,
        "hide_legend": false,
        "allow_symbol_change": false,
        "save_image": false,
        "studies": [
          {{"id": "MASimple@tv-basicstudies", "inputs": {{"length": 8}}}},
          {{"id": "MASimple@tv-basicstudies", "inputs": {{"length": 21}}}},
          {{"id": "MASimple@tv-basicstudies", "inputs": {{"length": 50}}}}
        ],
        "container_id": "{container_id}"
      }});
      </script>
    </div>
    """


def list_history_files():
    """Return sorted list of past scan CSVs (newest first)."""
    files = glob.glob(os.path.join(TMP_DIR, "scan_results_*.csv"))
    return sorted(files, reverse=True)


def grade_badge(grade: str) -> str:
    color = GRADE_COLORS.get(grade, "#888")
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">{grade}</span>'


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("🚀 Sean Scanner")
st.sidebar.caption('Scanner momentum — metodo "Back to Basics" (@SRxTrades)')

min_grade = st.sidebar.selectbox(
    "Grado minimo", ["A+", "A", "B", "C"], index=2,
    help="Soglia minima di qualità del setup da mostrare",
)

# ── Relative Strength weights (incl. 1-day) ──
with st.sidebar.expander("⚖️ Pesi Relative Strength", expanded=False):
    st.caption("Pesi per il punteggio dei settori. Ideale che sommino a 100%.")
    w1d = st.slider("1 giorno", 0, 100, int(WEIGHTS["1d"] * 100), 5) / 100
    w1w = st.slider("1 settimana", 0, 100, int(WEIGHTS["1w"] * 100), 5) / 100
    w1m = st.slider("1 mese", 0, 100, int(WEIGHTS["1m"] * 100), 5) / 100
    w3m = st.slider("3 mesi", 0, 100, int(WEIGHTS["3m"] * 100), 5) / 100
    tot = w1d + w1w + w1m + w3m
    if abs(tot - 1.0) > 0.001:
        st.warning(f"Somma pesi: {tot:.0%} (consigliato 100%)")
    else:
        st.success(f"Somma pesi: {tot:.0%}")
weights = {"1d": w1d, "1w": w1w, "1m": w1m, "3m": w3m}

# ── Universe / Level-1 filters ──
with st.sidebar.expander("🔧 Filtri universo (Livello 1)", expanded=False):
    top_n = st.slider("Numero settori leader", 1, 6, 3,
                      help="Quanti settori top usare come universo")
    max_per_sector = st.slider("Titoli max per settore", 10, 100, 60, 10)
    mc = st.selectbox("Market Cap minima", FILTER_OPTIONS["Market Cap."], index=1)
    pr = st.selectbox("Prezzo minimo", FILTER_OPTIONS["Price"], index=2)
    av = st.selectbox("Volume medio minimo", FILTER_OPTIONS["Average Volume"], index=2)
    rv = st.selectbox("Relative Volume minimo", FILTER_OPTIONS["Relative Volume"], index=2)

if st.sidebar.button("🔄 Esegui nuovo scan", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(
    "**Selezione titoli:**\n\n"
    "1. Settori leader (per Relative Strength)\n"
    "2. Titoli del settore (filtri universo)\n"
    "3. Scoring tecnico /16\n\n"
    "**Scoring /16:** trend mercato · EMA stack · "
    "compressione · volume pattern · candele · breakout"
)
st.sidebar.divider()
st.sidebar.caption("⚠️ Non è un consiglio finanziario. "
                   "Conferma sempre i setup manualmente.")


# ── Run scan (cached) ────────────────────────────────────────────────────────
weights_key = tuple(sorted(weights.items()))
filters_key = (mc, pr, av, rv)
with st.spinner("🔬 Scansione del mercato in corso (settori → titoli → scoring)..."):
    df, scan = run_full_scan(min_grade, weights_key, top_n, max_per_sector, filters_key)

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
    st.subheader("📊 Relative Strength — tutti i settori")

    p1d, p1w, p1m, p3m = (int(weights["1d"] * 100), int(weights["1w"] * 100),
                          int(weights["1m"] * 100), int(weights["3m"] * 100))
    st.markdown(
        f"""
**Legenda — come calcolo il punteggio (Relative Strength score):**

> `score = (perf_1giorno × {p1d}%) + (perf_1settimana × {p1w}%) + (perf_1mese × {p1m}%) + (perf_3mesi × {p3m}%)`

- **1 giorno → {p1d}%** — scatto odierno (dove ruotano i soldi proprio oggi)
- **1 settimana → {p1w}%** — momentum recente
- **1 mese → {p1m}%** — conferma che la forza dura, non è un rimbalzo di un giorno
- **3 mesi → {p3m}%** — contesto di fondo, filtra i falsi leader

I pesi sono modificabili dalla sidebar (⚖️). I top **{top_n}** settori alimentano la selezione titoli.
"""
    )

    sectors_all = load_all_sectors(weights_key)
    if sectors_all:
        sec_df = pd.DataFrame(sectors_all)
        sec_df = sec_df.rename(columns={
            "sector": "Settore", "perf_1d": "1 giorno", "perf_1w": "1 settimana",
            "perf_1m": "1 mese", "perf_3m": "3 mesi", "score": "Score",
        })
        top_sel = set(s["sector"] for s in sectors)

        def highlight_top(row):
            is_top = row["Settore"] in top_sel
            return ["background-color: #e8f5e9; font-weight: bold" if is_top else ""
                    for _ in row]

        styled = (sec_df.style
                  .apply(highlight_top, axis=1)
                  .format({"1 giorno": "{:+.2%}", "1 settimana": "{:+.2%}",
                           "1 mese": "{:+.2%}", "3 mesi": "{:+.2%}", "Score": "{:+.4f}"}))
        st.dataframe(styled, use_container_width=True, hide_index=True)
        st.caption(f"🟩 = top {top_n} settori selezionati che alimentano la selezione titoli. "
                   "Ordinati per Score decrescente.")

    st.divider()
    st.subheader("🎯 Titoli per settore leader")

    if funnel:
        for f in funnel:
            sec_score = next((s["score"] for s in sectors if s["sector"] == f["sector"]), 0)
            sec_df = df[df["Sector"] == f["sector"]]
            with st.expander(f"**{f['sector']}**  (score {sec_score:+.2f}) — {len(sec_df)} setup", expanded=True):
                if not sec_df.empty:
                    chips = "  ".join(
                        f"`{row.Ticker}` {row.Grade}" for row in sec_df.itertuples()
                    )
                    st.markdown(chips)
                else:
                    st.caption("Nessun setup di questo settore ha passato il grado minimo.")
    else:
        st.info("Dati settori non disponibili in questo scan.")

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
        table = view.copy()
        table["TradingView"] = table["Ticker"].apply(tradingview_url)
        st.dataframe(
            table[["Ticker", "TradingView", "Sector", "Industry", "Grade", "Score",
                   "Price", "VolPattern", "Candle", "NearBreakout"]],
            use_container_width=True, hide_index=True,
            column_config={
                "TradingView": st.column_config.LinkColumn(
                    "📈 TV", display_text="apri", help="Apri il grafico su TradingView"),
                "Score": st.column_config.ProgressColumn(
                    "Score", min_value=0, max_value=16, format="%.1f"),
                "NearBreakout": st.column_config.CheckboxColumn("⚡ BO"),
                "Price": st.column_config.NumberColumn("Prezzo", format="$%.2f"),
            },
        )

        csv = view.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Scarica CSV", csv,
                           f"scan_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

        # ── Inline TradingView charts (at-a-glance grid, asklivermore style) ──
        st.divider()
        gc1, gc2 = st.columns([3, 1])
        gc1.subheader("📊 Grafici TradingView")
        cols_per_row = gc2.selectbox("Colonne", [1, 2, 3], index=1,
                                     help="Quanti grafici per riga")
        show_charts = st.checkbox("Mostra grafici inline", value=True)

        if show_charts and not view.empty:
            chart_h = 380 if cols_per_row == 1 else (340 if cols_per_row == 2 else 300)
            tickers_to_show = view["Ticker"].tolist()
            for i in range(0, len(tickers_to_show), cols_per_row):
                row_tickers = tickers_to_show[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, tk in zip(cols, row_tickers):
                    r = view[view["Ticker"] == tk].iloc[0]
                    with col:
                        st.markdown(
                            f"**[{tk}]({tradingview_url(tk)})** · {r['Grade']} · "
                            f"{r['Score']}/16 · ${r['Price']:.2f}" +
                            ("  ⚡" if r["NearBreakout"] else ""))
                        desc = get_business_description(tk)
                        if desc:
                            st.caption(f"🏢 {desc}")
                        components.html(tradingview_widget_html(tk, chart_h),
                                        height=chart_h + 10)

# ── TAB 3: Chart ─────────────────────────────────────────────────────────────
with tab_chart:
    st.header("📈 Grafico setup")

    if df.empty:
        st.info("Nessun titolo da visualizzare.")
    else:
        sel = st.selectbox("Seleziona ticker", df["Ticker"].tolist())
        row = df[df["Ticker"] == sel].iloc[0]

        st.markdown(f"### [{sel}]({tradingview_url(sel)})  ·  {row['Sector']}")
        desc = get_business_description(sel)
        if desc:
            st.caption(f"🏢 {desc}")

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
