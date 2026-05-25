"""Streamlit frontend for the options pricing engines.

Run with:   streamlit run app.py
"""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from data import ModelInputs, get_inputs
from data.yahoo import get_expiries, get_options_chain, get_spot
from engines import binomial, greeks, monte_carlo

st.set_page_config(page_title="Options Pricer", layout="wide", page_icon="📈")


# --- Thin Streamlit cache layer on top of the disk cache so UI re-runs are instant ---
@st.cache_data(ttl=3600, show_spinner=False)
def cached_spot(ticker: str) -> float:
    return get_spot(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_expiries(ticker: str) -> list:
    return get_expiries(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_chain(ticker: str, expiry: str, option_type: str):
    return get_options_chain(ticker, expiry, option_type)


@st.cache_data(ttl=300, show_spinner=False)
def cached_inputs(ticker: str, expiry: str, strike: float, option_type: str):
    return get_inputs(ticker, expiry, strike, option_type)


st.title("Options Pricer")
st.caption("Binomial (CRR) and Monte Carlo (GBM) engines on live yfinance + FRED data")

# ─── Sidebar: contract & engine settings ────────────────────────────────
with st.sidebar:
    st.header("Contract")
    ticker = st.text_input("Ticker", "AAPL").strip().upper()

    try:
        spot = cached_spot(ticker)
        expiries = cached_expiries(ticker)
    except Exception as e:
        st.error(f"Could not load {ticker}: {e}")
        st.stop()

    if not expiries:
        st.error(f"No options chain for {ticker}.")
        st.stop()

    st.metric("Spot", f"${spot:,.2f}")
    expiry = st.selectbox("Expiry", expiries)
    option_type = st.radio("Type", ["call", "put"], horizontal=True)

    chain = cached_chain(ticker, expiry, option_type)
    strikes = sorted(chain["strike"].unique().tolist())
    atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    strike = st.selectbox(
        "Strike", strikes, index=atm_idx, format_func=lambda x: f"${x:,.2f}"
    )

    with st.expander("Engine settings"):
        n_steps = st.slider("Binomial steps", 50, 500, 200, 50)
        n_paths = st.slider("MC paths", 10_000, 500_000, 100_000, 10_000)
        american = st.checkbox("American exercise (binomial)", value=True)
        seed = st.number_input("MC seed", value=42, step=1)

# ─── Build inputs once ──────────────────────────────────────────────────
inputs = cached_inputs(ticker, expiry, strike, option_type)
row = chain.loc[chain["strike"] == strike].iloc[0]
bid, ask = float(row["bid"]), float(row["ask"])
market_mid = (bid + ask) / 2 if (bid > 0 and ask > 0) else None

# ─── Tabs ───────────────────────────────────────────────────────────────
tab_price, tab_greeks, tab_chain, tab_charts = st.tabs(
    ["Pricing", "Greeks", "Chain", "Charts"]
)

# ─── Tab 1: Pricing ─────────────────────────────────────────────────────
with tab_price:
    st.subheader(f"{ticker} {expiry} ${strike:,.2f} {option_type}")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("S (spot)", f"${inputs.S:,.2f}")
    c2.metric("K (strike)", f"${inputs.K:,.2f}")
    c3.metric("T (trading-yrs)", f"{inputs.T:.4f}")
    c4.metric("r (rate)", f"{inputs.r:.2%}")
    c5.metric("σ (IV)", f"{inputs.sigma:.2%}")
    c6.metric("q (div yield)", f"{inputs.q:.2%}")

    st.divider()

    bin_price = binomial.price(inputs, n_steps=n_steps, american=american)
    mc = monte_carlo.price(inputs, n_paths=n_paths, seed=int(seed))

    p1, p2, p3 = st.columns(3)
    exercise = "American" if american else "European"
    p1.metric(f"Binomial ({exercise}, {n_steps} steps)", f"${bin_price:.4f}")
    p2.metric(
        f"Monte Carlo (European, {mc.n_paths:,} paths)",
        f"${mc.price:.4f}",
        help=f"±${1.96 * mc.std_error:.4f} (95% CI)",
    )
    if market_mid is not None:
        p3.metric(
            "Market mid (bid/ask)",
            f"${market_mid:.4f}",
            delta=f"{(bin_price - market_mid):+.4f} vs binomial",
        )
    else:
        p3.metric("Market mid", "—", help="No bid/ask available")

# ─── Tab 2: Greeks ──────────────────────────────────────────────────────
with tab_greeks:
    st.subheader("Greeks (finite-difference against binomial)")
    g = greeks.compute(inputs, n_steps=n_steps, american=american)

    g1, g2, g3, g4, g5 = st.columns(5)
    g1.metric("Δ Delta", f"{g.delta:.4f}", help="∂V/∂S per $1 move in underlying")
    g2.metric("Γ Gamma", f"{g.gamma:.6f}", help="∂²V/∂S² per $1²")
    g3.metric("ν Vega", f"{g.vega:.4f}", help="∂V/∂σ per 1 vol-point (sigma += 0.01)")
    g4.metric("Θ Theta", f"{g.theta:.4f}", help="Per calendar day — negative = decay")
    g5.metric("ρ Rho", f"{g.rho:.4f}", help="∂V/∂r per 1% rate change")

    st.caption(
        "Delta = how much the option moves per $1 underlying move. "
        "Gamma = how fast delta changes. "
        "Vega = sensitivity to volatility. "
        "Theta = time decay per day. "
        "Rho = sensitivity to interest rates."
    )

# ─── Tab 3: Chain ───────────────────────────────────────────────────────
with tab_chain:
    st.subheader(f"{ticker} {option_type} chain — {expiry}")
    display = chain[
        ["strike", "bid", "ask", "lastPrice", "impliedVolatility", "volume", "openInterest"]
    ].copy()
    display.columns = ["Strike", "Bid", "Ask", "Last", "IV", "Volume", "OI"]
    display["IV"] = display["IV"] * 100  # decimal → percent for display
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config={
            "Strike": st.column_config.NumberColumn(format="$%.2f"),
            "Bid": st.column_config.NumberColumn(format="$%.2f"),
            "Ask": st.column_config.NumberColumn(format="$%.2f"),
            "Last": st.column_config.NumberColumn(format="$%.2f"),
            "IV": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

# ─── Tab 4: Charts ──────────────────────────────────────────────────────
with tab_charts:
    bin_price = binomial.price(inputs, n_steps=n_steps, american=american)

    # ---- Payoff at expiry ----
    st.subheader("Payoff at expiry")
    s_range = np.linspace(inputs.K * 0.5, inputs.K * 1.5, 200)
    if option_type == "call":
        payoff = np.maximum(s_range - inputs.K, 0)
    else:
        payoff = np.maximum(inputs.K - s_range, 0)
    pnl = payoff - bin_price

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s_range, y=payoff, name="Payoff at expiry", line=dict(width=2)))
    fig.add_trace(go.Scatter(x=s_range, y=pnl, name="P&L (after premium)", line=dict(width=2, dash="dash")))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.add_vline(x=inputs.K, line_dash="dot", annotation_text=f"K=${inputs.K:.0f}")
    fig.add_vline(x=inputs.S, line_dash="dot", line_color="green", annotation_text=f"S=${inputs.S:.0f}")
    fig.update_layout(xaxis_title="Underlying price at expiry", yaxis_title="Value ($)", height=400)
    st.plotly_chart(fig)

    # ---- Model vs market across the IV smile ----
    st.subheader("Model price vs strike (using each strike's own IV)")
    strikes_arr = chain["strike"].values
    ivs_arr = chain["impliedVolatility"].values
    bid_arr = chain["bid"].values
    ask_arr = chain["ask"].values
    market_mids = np.where(
        (bid_arr > 0) & (ask_arr > 0), (bid_arr + ask_arr) / 2, np.nan
    )

    model_prices = []
    for K_i, sig_i in zip(strikes_arr, ivs_arr):
        if sig_i is None or np.isnan(sig_i) or sig_i <= 0:
            model_prices.append(np.nan)
            continue
        inp_i = ModelInputs(
            S=inputs.S, K=float(K_i), T=inputs.T, r=inputs.r,
            sigma=float(sig_i), q=inputs.q,
            option_type=option_type, ticker=ticker, expiry=expiry,
        )
        # 100 steps keeps the chart-wide recompute snappy
        model_prices.append(binomial.price(inp_i, n_steps=100, american=american))

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=strikes_arr, y=market_mids, name="Market mid",
                              mode="markers+lines", marker=dict(size=8)))
    fig2.add_trace(go.Scatter(x=strikes_arr, y=model_prices, name="Binomial (per-strike IV)",
                              mode="markers+lines", marker=dict(size=6)))
    fig2.add_vline(x=inputs.K, line_dash="dot", annotation_text="Selected")
    fig2.add_vline(x=inputs.S, line_dash="dot", line_color="green", annotation_text="Spot")
    fig2.update_layout(xaxis_title="Strike ($)", yaxis_title="Option price ($)", height=400)
    st.plotly_chart(fig2)
