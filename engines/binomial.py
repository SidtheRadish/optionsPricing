"""Cox-Ross-Rubinstein binomial tree option pricer.

Handles American and European calls/puts on dividend-paying stocks. The
dividend yield enters the risk-neutral drift as ``(r - q)``.
"""
import math

import numpy as np

from data import ModelInputs


def price(inputs: ModelInputs, n_steps: int = 200, american: bool = True) -> float:
    """Option price under a CRR binomial tree.

    ``n_steps`` controls accuracy/runtime (~O(n²)). 200 is a good default for
    short-dated equity options. Set ``american=False`` for European exercise.
    """
    S, K, T = inputs.S, inputs.K, inputs.T
    r, sigma, q = inputs.r, inputs.sigma, inputs.q
    is_call = inputs.option_type == "call"

    if T <= 0:
        return max(S - K, 0.0) if is_call else max(K - S, 0.0)

    dt = T / n_steps
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    p = (math.exp((r - q) * dt) - d) / (u - d)

    # Terminal asset prices: node j has price S * u^(n-j) * d^j
    j = np.arange(n_steps + 1)
    prices = S * (u ** (n_steps - j)) * (d ** j)
    values = np.maximum(prices - K, 0.0) if is_call else np.maximum(K - prices, 0.0)

    # Walk the tree backward
    for step in range(n_steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1.0 - p) * values[1:])
        if american:
            j = np.arange(step + 1)
            node_prices = S * (u ** (step - j)) * (d ** j)
            intrinsic = (
                np.maximum(node_prices - K, 0.0)
                if is_call
                else np.maximum(K - node_prices, 0.0)
            )
            values = np.maximum(values, intrinsic)

    return float(values[0])
