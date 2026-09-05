from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from src.analysis.indicators import add_indicators

st.set_page_config(page_title="AI Investment — Live Guidance", page_icon="📈", layout="wide")

BACKEND_URL = "http://localhost:8000"
INTERVALS = ["1m", "3m", "5m", "10m", "15m", "30m", "1h"]

for key, default in {
    "instrument": None,
    "search_results": [],
    "search_query": "",
    "running": False,
    "interval": "1m",
    "analysis": None,
    "last_state": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def api(method, endpoint, **kwargs):
    response = requests.request(method, f"{BACKEND_URL}{endpoint}", timeout=15, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}


def money(v):
    if v is None:
        return "—"
    try:
        return f"₹{float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def number(v):
    if v is None:
        return "—"
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def pct(v):
    if v is None:
        return "—"
    try:
        return f"{float(v):.0f}%"
    except (TypeError, ValueError):
        return "—"


def signal_meta(signal):
    signal = (signal or "HOLD").upper()
    return {
        "BUY": ("BUY", "#00a86b", "#e8fff6"),
        "SELL": ("SELL", "#d7263d", "#fff0f2"),
        "HOLD": ("HOLD", "#b77900", "#fff8df"),
    }.get(signal, ("HOLD", "#b77900", "#fff8df"))


def fetch_state():
    return api("GET", "/live/state")


def fetch_analysis():
    payload = api("GET", "/live/analysis")
    value = payload.get("analysis") if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else None


def fetch_candles():
    payload = api("GET", "/live/candles")
    candles = payload.get("candles", []) if isinstance(payload, dict) else []
    return candles if isinstance(candles, list) else []


def fetch_current_candle():
    payload = api("GET", "/live/current-candle")
    value = payload.get("candle") if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else None


def search_market(query):
    payload = api("POST", "/live/search", json={"query": query.strip()})
    return payload.get("instruments", []) if isinstance(payload, dict) else []


def render_instrument_picker():
    with st.popover("🔎 Change instrument", use_container_width=False):
        query = st.text_input("Search NSE instrument", value=st.session_state["search_query"], placeholder="HDFCBANK, TCS, RELIANCE…")
        if st.button("Search Upstox", type="primary", use_container_width=True):
            try:
                st.session_state["search_query"] = query
                st.session_state["search_results"] = search_market(query)
            except Exception as exc:
                st.error(str(exc))

        results = st.session_state["search_results"]
        if results:
            labels = [f"{r.get('trading_symbol', '—')} — {r.get('name', '')}" for r in results]
            current = st.session_state.get("instrument") or {}
            current_key = current.get("instrument_key")
            index = next((i for i, r in enumerate(results) if r.get("instrument_key") == current_key), 0)
            choice = st.selectbox("Instrument", labels, index=index)
            selected = results[labels.index(choice)]
            if selected.get("instrument_key") != current_key:
                st.session_state["instrument"] = selected
                st.session_state["analysis"] = None
                st.session_state["last_state"] = None
                st.session_state["running"] = False
            st.caption(f"{selected.get('exchange', '')} • {selected.get('instrument_type', '')} • {selected.get('instrument_key', '')}")
        elif query:
            st.info("No matching NSE instrument found.")


def build_chart(candles, current_candle, analysis, symbol, interval):
    rows = list(candles)
    if current_candle:
        if not rows or str(current_candle.get("timestamp")) > str(rows[-1].get("timestamp")):
            rows.append(current_candle)
    if not rows:
        return None

    df = pd.DataFrame(rows)
    needed = {"timestamp", "open", "high", "low", "close", "volume"}
    if not needed.issubset(df.columns):
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).drop_duplicates("timestamp").sort_values("timestamp")
    if df.empty:
        return None
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        return None

    calc = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}).set_index("timestamp")
    try:
        calc = add_indicators(calc)
    except Exception:
        calc = calc

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["timestamp"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        name=symbol,
        increasing_line_color="#18a66d",
        increasing_fillcolor="#18a66d",
        decreasing_line_color="#e0445b",
        decreasing_fillcolor="#e0445b",
        whiskerwidth=0.7,
    ))

    # High-value overlays only; detailed indicators remain below the chart.
    for column, name, dash in [("EMA_20", "EMA 20", "solid"), ("EMA_50", "EMA 50", "dash"), ("VWAP", "VWAP", "dot")]:
        if column in calc:
            fig.add_trace(go.Scatter(x=calc.index, y=calc[column], mode="lines", name=name, line=dict(width=1.5, dash=dash)))

    decision = (analysis or {}).get("decision", {})
    trade = (analysis or {}).get("trade_plan", {})
    technical = (analysis or {}).get("technical_signal", {})
    snapshot = (analysis or {}).get("snapshot", {})
    signal = decision.get("final_signal", "HOLD")
    signal_text, signal_color, signal_bg = signal_meta(signal)

    # Current live price is authoritative for the entry marker.
    live_price = snapshot.get("price")
    if live_price is None and current_candle:
        live_price = current_candle.get("close")
    if live_price is not None:
        fig.add_hline(y=float(live_price), line_width=1.5, line_dash="solid", line_color="#5b6470",
                      annotation_text=f"LIVE {money(live_price)}", annotation_position="top left")

    levels = []
    if trade.get("entry") is not None:
        levels.append(("ENTRY", trade["entry"], "#2f6fed"))
    if trade.get("stop_loss") is not None:
        levels.append(("STOP", trade["stop_loss"], "#d7263d"))
    if trade.get("target_1") is not None:
        levels.append(("TARGET 1", trade["target_1"], "#00a86b"))
    if trade.get("target_2") is not None:
        levels.append(("TARGET 2", trade["target_2"], "#00a86b"))
    if trade.get("trailing_stop") is not None:
        levels.append(("TRAIL", trade["trailing_stop"], "#8a5cf6"))

    # HOLD: show structure/monitoring levels instead of fake trade targets.
    if signal == "HOLD":
        if trade.get("support") is not None:
            levels.append(("SUPPORT", trade["support"], "#d08a00"))
        if trade.get("resistance") is not None:
            levels.append(("RESISTANCE", trade["resistance"], "#d08a00"))

    for label, value, color in levels:
        fig.add_hline(y=float(value), line_width=1.2, line_dash="dash", line_color=color,
                      annotation_text=f"{label}  {money(value)}", annotation_position="top right")

    strategy_count = technical.get("strategy_count", 0)
    alignment = technical.get("technical_alignment")
    confidence = decision.get("ai_confidence")
    trend = decision.get("trend", "—")
    momentum = decision.get("momentum", "—")

    panel = (
        f"<b style='font-size:28px'>{signal_text}</b><br>"
        f"<span style='font-size:13px'>AI {pct(confidence)} · Technical {pct(alignment)}</span><br>"
        f"<span style='font-size:12px'>{trend} · {momentum}</span>"
    )
    fig.add_annotation(x=0.985, y=0.985, xref="paper", yref="paper", xanchor="right", yanchor="top",
                       text=panel, showarrow=False, align="center", bgcolor=signal_bg, bordercolor=signal_color,
                       borderwidth=2, borderpad=12, font=dict(color=signal_color))

    confluence = (
        f"<b>Guidance confluence</b><br>"
        f"Strategies evaluated: {strategy_count}<br>"
        f"Bull score: {technical.get('bullish_score', '—')} · Bear score: {technical.get('bearish_score', '—')}"
    )
    fig.add_annotation(x=0.015, y=0.985, xref="paper", yref="paper", xanchor="left", yanchor="top",
                       text=confluence, showarrow=False, align="left", bgcolor="rgba(255,255,255,0.90)",
                       bordercolor="#cfd5dc", borderwidth=1, borderpad=8, font=dict(size=11, color="#26313d"))

    fig.update_layout(
        height=720,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        dragmode="pan",
        showlegend=True,
        legend=dict(orientation="h", y=1.01, x=0),
        xaxis=dict(
            type="date", showgrid=True, gridcolor="#edf0f3", rangeslider=dict(visible=True, thickness=0.08),
            rangeselector=dict(buttons=[dict(count=1, label="1D", step="day", stepmode="backward"),
                                       dict(count=3, label="3D", step="day", stepmode="backward"),
                                       dict(step="all", label="ALL")]),
        ),
        yaxis=dict(showgrid=True, gridcolor="#edf0f3", fixedrange=False, side="right", tickprefix="₹"),
        uirevision=f"{symbol}-{interval}",
    )
    fig.update_xaxes(rangeslider_bgcolor="#f4f6f8")
    return fig


def render_details(analysis):
    if not analysis:
        return
    snapshot = analysis.get("snapshot", {})
    technical = analysis.get("technical_signal", {})
    ai = analysis.get("ai_analysis", {})
    decision = analysis.get("decision", {})
    risk = analysis.get("risk", {})
    trade = analysis.get("trade_plan", {})

    st.subheader("Detailed guidance")
    a, b, c, d = st.columns(4)
    a.metric("RSI", number(snapshot.get("rsi_14")))
    b.metric("ATR", money(snapshot.get("atr_14")))
    c.metric("VWAP", money(snapshot.get("vwap")))
    d.metric("ADX", number(snapshot.get("adx_14")))

    with st.expander("Strategy confluence", expanded=False):
        for item in technical.get("strategies", []):
            st.write(f"**{item.get('name')}** — {item.get('signal')}: {item.get('reason')}")

    with st.expander("AI interpretation", expanded=False):
        st.write(ai.get("summary", "No AI summary available."))
        for reason in ai.get("reasons", []):
            st.write(f"• {reason}")

    with st.expander("Risk and execution plan", expanded=False):
        st.write(f"**Risk:** {risk.get('risk', '—')} · Score: {risk.get('risk_score', '—')}")
        st.write(f"**Position size:** {trade.get('position_size', 0)}")
        st.write(f"**Risk/share:** {money(trade.get('risk_per_share'))}")
        st.write(f"**Trailing stop:** {money(trade.get('trailing_stop'))}")
        st.write(trade.get("reason", "No plan information."))

    with st.expander("All calculated indicators", expanded=False):
        st.json(snapshot)


def live_panel():
    instrument = st.session_state.get("instrument")
    if not instrument or not st.session_state.get("running"):
        return

    try:
        state = fetch_state()
        st.session_state["last_state"] = state
        analysis = fetch_analysis()
        if analysis:
            st.session_state["analysis"] = analysis
        else:
            analysis = st.session_state.get("analysis")
        candles = fetch_candles()
        current = fetch_current_candle()
    except requests.exceptions.ConnectionError:
        st.error("Backend unavailable. Start FastAPI before starting the live market.")
        return
    except Exception as exc:
        st.warning(f"Live refresh issue: {exc}")
        state = st.session_state.get("last_state") or {}
        analysis = st.session_state.get("analysis")
        candles = []
        current = None

    symbol = instrument.get("trading_symbol", "Market")
    interval = state.get("selected_interval", st.session_state["interval"])
    st.session_state["interval"] = interval

    latest_tick = state.get("latest_tick") or {}
    ws = state.get("websocket_connected")
    last_message = state.get("last_websocket_message_at")
    status = "CONNECTING"
    if ws is True:
        status = "LIVE" if latest_tick else "CONNECTED · WAITING FOR TICK"
    elif state.get("websocket_error"):
        status = "RECONNECTING"

    analysis = analysis if isinstance(analysis, dict) else {}
    decision = analysis.get("decision", {})
    trade = analysis.get("trade_plan", {})
    snapshot = analysis.get("snapshot", {})
    signal = decision.get("final_signal", "HOLD")
    signal_text, color, bg = signal_meta(signal)

    title_col, status_col, controls_col = st.columns([5, 2, 3])
    with title_col:
        st.markdown(f"# {symbol}")
        st.caption(f"Upstox live market guidance · {interval}")
    with status_col:
        st.markdown(f"### :{'green' if status == 'LIVE' else 'orange'}[{status}]")
        if latest_tick.get("price") is not None:
            st.caption(f"LTP {money(latest_tick.get('price'))}")
    with controls_col:
        cols = st.columns(len(INTERVALS))
        for col, item in zip(cols, INTERVALS):
            with col:
                if st.button(item, key=f"tf_{item}", type="primary" if item == interval else "secondary", use_container_width=True):
                    try:
                        api("POST", "/live/interval", json={"interval": item})
                        st.session_state["interval"] = item
                        st.session_state["analysis"] = None
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))

    st.markdown(
        f"<div style='border-left:5px solid {color}; background:{bg}; padding:9px 14px; margin-bottom:8px;'>"
        f"<b>{signal_text}</b> · {decision.get('trend','—')} · {decision.get('momentum','—')} · "
        f"AI {pct(decision.get('ai_confidence'))} · Technical {pct(decision.get('technical_alignment'))}</div>",
        unsafe_allow_html=True,
    )

    fig = build_chart(candles, current, analysis, symbol, interval)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True, "responsive": True})
    else:
        st.info("Waiting for candle data…")

    # Important execution summary directly below the chart.
    t1, t2, t3, t4, t5, t6 = st.columns(6)
    t1.metric("Entry", money(trade.get("entry")))
    t2.metric("Stop", money(trade.get("stop_loss")))
    t3.metric("Target 1", money(trade.get("target_1")))
    t4.metric("Target 2", money(trade.get("target_2")))
    t5.metric("Qty", trade.get("position_size", 0))
    t6.metric("R:R", f"1:{trade.get('risk_reward_1','—')} / 1:{trade.get('risk_reward_2','—')}")

    if signal == "HOLD":
        st.caption(f"HOLD monitoring zone · Support {money(trade.get('support'))} · Resistance {money(trade.get('resistance'))} · {trade.get('reason','')}")

    st.divider()
    render_details(analysis)


# Header / instrument selection
left, right = st.columns([8, 2])
with left:
    st.markdown("# 📈 AI Investment")
    st.caption("A live trading chart with deterministic technical confluence, AI interpretation and risk-aware guidance.")
with right:
    render_instrument_picker()

instrument = st.session_state.get("instrument")
if instrument:
    symbol = instrument.get("trading_symbol", "Instrument")
    top1, top2, top3 = st.columns([5, 2, 2])
    with top1:
        st.markdown(f"### {symbol}  ·  {instrument.get('name','')}")
    with top2:
        if not st.session_state["running"]:
            if st.button("▶ Start Live", type="primary", use_container_width=True):
                try:
                    api("POST", "/live/start", json={"instrument": instrument, "interval": st.session_state["interval"]})
                    st.session_state["running"] = True
                    st.session_state["analysis"] = None
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            if st.button("⏹ Stop", use_container_width=True):
                try:
                    api("POST", "/live/stop")
                    st.session_state["running"] = False
                    st.session_state["analysis"] = None
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    with top3:
        st.caption("Instrument key")
        st.code(instrument.get("instrument_key", "—"), language=None)
else:
    st.info("Use **🔎 Change instrument** above to search Upstox and select an NSE instrument.")

if st.session_state.get("running"):
    if hasattr(st, "fragment"):
        @st.fragment(run_every=2)
        def _live_fragment():
            live_panel()
        _live_fragment()
    else:
        live_panel()
else:
    st.caption("Select an instrument, then start the live market feed.")
