"""Smoke test: pull live inputs for an AAPL call and price it with both engines."""
from data import get_inputs
from data.yahoo import get_expiries, get_options_chain, get_spot
from engines import binomial, monte_carlo

TICKER = "AAPL"

spot = get_spot(TICKER)
expiries = get_expiries(TICKER)
print(f"{TICKER} spot: ${spot:.2f}")
print(f"Available expiries (first 5): {expiries[:5]}")

# Pick an expiry ~2 weeks out and the at-the-money strike
expiry = expiries[10] if len(expiries) > 10 else expiries[-1]
chain = get_options_chain(TICKER, expiry, "call")
atm_row = chain.iloc[(chain["strike"] - spot).abs().argsort().iloc[0]]
strike = float(atm_row["strike"])
market_mid = float((atm_row["bid"] + atm_row["ask"]) / 2)

inputs = get_inputs(TICKER, expiry, strike, "call")
print(f"\nInputs for {TICKER} {expiry} ${strike:.2f} call:")
print(f"  S     = {inputs.S:.4f}")
print(f"  K     = {inputs.K:.4f}")
print(f"  T     = {inputs.T:.6f} (trading-day years)")
print(f"  r     = {inputs.r:.4%}")
print(f"  sigma = {inputs.sigma:.4%} (implied)")
print(f"  q     = {inputs.q:.4%} (trailing dividend yield)")

bin_amer = binomial.price(inputs, n_steps=200, american=True)
bin_euro = binomial.price(inputs, n_steps=200, american=False)
mc = monte_carlo.price(inputs, n_paths=100_000, seed=42)

print(f"\nPrices:")
print(f"  Binomial (American, 200 steps): ${bin_amer:.4f}")
print(f"  Binomial (European, 200 steps): ${bin_euro:.4f}")
print(f"  Monte Carlo (European, {mc.n_paths:,} paths): ${mc.price:.4f} ± {1.96 * mc.std_error:.4f} (95% CI)")
print(f"  Market mid (bid/ask): ${market_mid:.4f}")
