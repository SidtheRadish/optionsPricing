"""Finite-difference Greeks computed against the binomial engine.

Bumps each input and reprices to estimate first/second derivatives. Output
conventions match typical option-desk quoting:

  Delta:  per $1 move in underlying
  Gamma:  per $1^2 move
  Vega:   per 1 vol-point  (sigma += 0.01)
  Theta:  per calendar day (negative for long options)
  Rho:    per 1% rate change (r += 0.01)
"""
from dataclasses import dataclass, replace

from data import ModelInputs

from . import binomial

# One calendar day expressed in our T units (T uses 252 trading-day years;
# wall-clock-wise, 1 trading year ~ 1 calendar year ~ 365 days).
ONE_CAL_DAY_T = 1.0 / 365.0


@dataclass
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


def compute(inputs: ModelInputs, n_steps: int = 200, american: bool = True) -> Greeks:
    base = binomial.price(inputs, n_steps, american)

    # Delta uses a small bump for accuracy.
    dS_d = max(inputs.S * 0.01, 0.01)
    up_d = binomial.price(replace(inputs, S=inputs.S + dS_d), n_steps, american)
    dn_d = binomial.price(replace(inputs, S=inputs.S - dS_d), n_steps, american)
    delta = (up_d - dn_d) / (2 * dS_d)

    # Gamma uses a larger bump (5% of S). CRR's discrete node alignment
    # makes the price function staircase at small dS, which inflates the
    # second-difference estimate. A larger bump averages over many nodes.
    dS_g = max(inputs.S * 0.05, 0.50)
    up_g = binomial.price(replace(inputs, S=inputs.S + dS_g), n_steps, american)
    dn_g = binomial.price(replace(inputs, S=inputs.S - dS_g), n_steps, american)
    gamma = (up_g - 2 * base + dn_g) / (dS_g ** 2)

    # Vega: per 1 vol-point (sigma += 0.01)
    dv = 0.01
    v_up = binomial.price(replace(inputs, sigma=inputs.sigma + dv), n_steps, american)
    v_dn = binomial.price(replace(inputs, sigma=max(inputs.sigma - dv, 1e-6)), n_steps, american)
    vega = (v_up - v_dn) / 2

    # Theta: per calendar day passing (T shrinks by 1/365)
    if inputs.T > ONE_CAL_DAY_T:
        t_dn = binomial.price(replace(inputs, T=inputs.T - ONE_CAL_DAY_T), n_steps, american)
        theta = t_dn - base  # negative for long options
    else:
        theta = 0.0

    # Rho: per 1% rate change (r += 0.01)
    dr = 0.01
    r_up = binomial.price(replace(inputs, r=inputs.r + dr), n_steps, american)
    r_dn = binomial.price(replace(inputs, r=inputs.r - dr), n_steps, american)
    rho = (r_up - r_dn) / 2

    return Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)
