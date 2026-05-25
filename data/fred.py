"""FRED API client for the US Treasury constant-maturity yield curve.

Requires the ``FRED_API_KEY`` environment variable. Get a free key at
https://fred.stlouisfed.org/docs/api/api_key.html.
"""
import os

import requests

from .cache import cached

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

# Maturity (years) -> FRED series ID for the constant-maturity Treasury yield
TREASURY_SERIES = {
    1 / 12: "DGS1MO",
    3 / 12: "DGS3MO",
    6 / 12: "DGS6MO",
    1:      "DGS1",
    2:      "DGS2",
    3:      "DGS3",
    5:      "DGS5",
    7:      "DGS7",
    10:     "DGS10",
    20:     "DGS20",
    30:     "DGS30",
}


@cached(ttl_seconds=86400)
def _fetch_latest_yield(series_id: str) -> float:
    """Latest annualized yield as a decimal (0.0525 == 5.25%)."""
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY env var not set. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,  # latest reading is sometimes "." on holidays
    }
    resp = requests.get(FRED_URL, params=params, timeout=10)
    resp.raise_for_status()
    for obs in resp.json()["observations"]:
        if obs["value"] != ".":
            return float(obs["value"]) / 100.0
    raise RuntimeError(f"No recent valid observation for {series_id}")


def get_treasury_yield(maturity_years: float) -> float:
    """Constant-maturity Treasury yield (decimal) at the given maturity,
    linearly interpolated between the two bracketing FRED tenors."""
    tenors = sorted(TREASURY_SERIES.keys())
    if maturity_years <= tenors[0]:
        return _fetch_latest_yield(TREASURY_SERIES[tenors[0]])
    if maturity_years >= tenors[-1]:
        return _fetch_latest_yield(TREASURY_SERIES[tenors[-1]])
    lower = max(t for t in tenors if t <= maturity_years)
    upper = min(t for t in tenors if t >= maturity_years)
    y_lo = _fetch_latest_yield(TREASURY_SERIES[lower])
    y_hi = _fetch_latest_yield(TREASURY_SERIES[upper])
    if lower == upper:
        return y_lo
    w = (maturity_years - lower) / (upper - lower)
    return y_lo + w * (y_hi - y_lo)
