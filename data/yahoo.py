"""yfinance wrappers: spot, options chain, dividends, expiries.

All calls go through the local pickle cache so repeated runs don't hammer
Yahoo's endpoints (which rate-limit and occasionally flake).
"""
import pandas as pd
import yfinance as yf

from .cache import cached


@cached(ttl_seconds=3600)  # 1 hour
def get_spot(ticker: str) -> float:
    """Latest traded price for the underlying."""
    return float(yf.Ticker(ticker).fast_info["last_price"])


@cached(ttl_seconds=3600)
def get_expiries(ticker: str) -> list[str]:
    """List of available option expiry dates as 'YYYY-MM-DD' strings."""
    return list(yf.Ticker(ticker).options)


@cached(ttl_seconds=3600)
def get_options_chain(ticker: str, expiry: str, option_type: str) -> pd.DataFrame:
    """Calls or puts DataFrame for the given expiry.

    Columns include: strike, bid, ask, lastPrice, impliedVolatility, volume,
    openInterest. option_type must be 'call' or 'put'.
    """
    chain = yf.Ticker(ticker).option_chain(expiry)
    return chain.calls if option_type == "call" else chain.puts


@cached(ttl_seconds=86400)  # 1 day
def get_dividends(ticker: str) -> pd.Series:
    """Historical dividend payments indexed by ex-date."""
    return yf.Ticker(ticker).dividends
