# optionsPricing

Python implementations of the **binomial** and **Monte Carlo** option pricing models for equity options, fed by live market data.

## Project layout

```
data/
  yahoo.py         # yfinance wrappers (spot, options chain, dividends)
  fred.py          # FRED Treasury yield client
  cache.py         # local pickle cache for API responses
  inputs.py        # assembles ModelInputs from the above
engines/
  binomial.py      # CRR binomial tree pricer
  monte_carlo.py   # GBM Monte Carlo pricer
main.py            # entry point / smoke test
```

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Get a free FRED API key at https://fred.stlouisfed.org/docs/api/api_key.html and put it in a `.env` file at the project root (gitignored):
   ```
   FRED_API_KEY=your_key_here
   ```
3. Run the smoke test:
   ```
   python main.py
   ```

## Data sources

All inputs to the pricing models are pulled from free APIs:

| Input | Source |
|---|---|
| Spot price, options chain, dividends, price history | [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance, no API key) |
| Risk-free rate (Treasury yields) | [FRED](https://fred.stlouisfed.org/) (free API key) |

## Modeling decisions

### Volatility: Implied (IV)

We use **implied volatility** pulled per-contract from the yfinance options chain — not historical volatility.

- **Historical Volatility (HV)** is computed from past price data (std dev of daily log returns, annualized). It tells you how volatile the stock *has been*.
- **Implied Volatility (IV)** is reverse-engineered from the current market price of a traded option — the σ that makes Black-Scholes match the market. It tells you what the market *expects* future volatility to be.

We chose IV because it calibrates our model to the current market, which is the more accurate signal for pricing a *listed* option. HV would be the better choice if we were trying to forecast fair value independently of the options market.

### Day-count convention: Trading/252

Time-to-expiry `T` and annualized volatility `σ` are both expressed using a **252 trading-day** year (not 365 calendar). This is more accurate for equity volatility because stocks don't move on weekends or holidays. Both `T` and `σ` must use the same convention — never mix.

### Risk-free rate: FRED Treasury curve

We pull the Treasury yield matching the option's maturity (`DGS1MO`, `DGS3MO`, `DGS6MO`, `DGS1`, `DGS2`, ...) and interpolate between tenors when the expiry falls in between.

### Dividends: discrete schedule

We use the discrete dividend history from `yfinance.Ticker(...).dividends` and project the cadence forward, rather than approximating with a flat continuous yield. This is strictly more accurate, especially for American options where ex-dividend dates affect early-exercise behavior.

### Caching

API responses are cached to local disk so the model can be re-run without re-hitting the network every time. This keeps iteration fast, avoids rate limits, and makes results reproducible. Stale-cache thresholds: ~1 hour for prices/chains, ~1 day for dividends/rates.
