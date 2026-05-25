"""Assemble the full set of model inputs (S, K, T, r, sigma, q) for a single
listed option contract by combining yfinance + FRED.
"""
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from . import fred, yahoo

TRADING_DAYS_PER_YEAR = 252


@dataclass
class ModelInputs:
    S: float            # spot price
    K: float            # strike
    T: float            # time to expiry, in 252-trading-day years
    r: float            # risk-free rate (decimal)
    sigma: float        # implied volatility (decimal)
    q: float            # trailing dividend yield (decimal)
    option_type: str    # 'call' or 'put'
    ticker: str
    expiry: str         # 'YYYY-MM-DD'


def _trading_days_to_expiry(expiry: str) -> float:
    expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").date()
    today = date.today()
    if expiry_dt <= today:
        return 0.0
    # bdate_range is inclusive on both ends; subtract 1 so an expiry on the
    # next business day gives T = 1/252, not 2/252.
    bdays = len(pd.bdate_range(today, expiry_dt)) - 1
    return bdays / TRADING_DAYS_PER_YEAR


def _trailing_dividend_yield(ticker: str, spot: float) -> float:
    divs = yahoo.get_dividends(ticker)
    if divs.empty:
        return 0.0
    cutoff = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
    trailing = divs[divs.index >= cutoff].sum()
    return float(trailing / spot)


def get_inputs(
    ticker: str,
    expiry: str,
    strike: float,
    option_type: str = "call",
) -> ModelInputs:
    """Pull all inputs needed to price a single listed option contract.

    ``expiry`` must match one of the dates returned by ``yahoo.get_expiries``.
    """
    if option_type not in ("call", "put"):
        raise ValueError(f"option_type must be 'call' or 'put', got {option_type!r}")

    spot = yahoo.get_spot(ticker)
    chain = yahoo.get_options_chain(ticker, expiry, option_type)
    row = chain.loc[chain["strike"] == strike]
    if row.empty:
        nearest = chain.iloc[(chain["strike"] - strike).abs().argsort()[:5]]
        raise ValueError(
            f"No {option_type} found for {ticker} {expiry} K={strike}. "
            f"Nearest strikes: {nearest['strike'].tolist()}"
        )
    iv = float(row["impliedVolatility"].iloc[0])

    T = _trading_days_to_expiry(expiry)
    r = fred.get_treasury_yield(T) if T > 0 else 0.0
    q = _trailing_dividend_yield(ticker, spot)

    return ModelInputs(
        S=spot, K=strike, T=T, r=r, sigma=iv, q=q,
        option_type=option_type, ticker=ticker, expiry=expiry,
    )
