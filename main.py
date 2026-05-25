"""Smoke test: pull live inputs for an AAPL call and print them."""
from data import get_inputs
from data.yahoo import get_expiries, get_options_chain, get_spot

TICKER = "AAPL"

spot = get_spot(TICKER)
expiries = get_expiries(TICKER)
print(f"{TICKER} spot: ${spot:.2f}")
print(f"Available expiries (first 5): {expiries[:5]}")

# Pick the nearest expiry and the at-the-money strike from that chain
expiry = expiries[0]
chain = get_options_chain(TICKER, expiry, "call")
strike = float(chain.iloc[(chain["strike"] - spot).abs().argsort().iloc[0]]["strike"])

inputs = get_inputs(TICKER, expiry, strike, "call")
print(f"\nInputs for {TICKER} {expiry} ${strike:.2f} call:")
print(f"  S     = {inputs.S:.4f}")
print(f"  K     = {inputs.K:.4f}")
print(f"  T     = {inputs.T:.6f} (trading-day years)")
print(f"  r     = {inputs.r:.4%}")
print(f"  sigma = {inputs.sigma:.4%} (implied)")
print(f"  q     = {inputs.q:.4%} (trailing dividend yield)")
