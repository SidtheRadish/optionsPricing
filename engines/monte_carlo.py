"""European option pricer via Monte Carlo simulation of geometric Brownian
motion.

European exercise only. American Monte Carlo requires Longstaff-Schwartz
regression and is out of scope for v1 — use the binomial engine for American.
"""
import math
from dataclasses import dataclass
from typing import Optional

import numpy as np

from data import ModelInputs


@dataclass
class MCResult:
    price: float        # discounted mean payoff
    std_error: float    # standard error of the estimate (for 95% CI use 1.96 * std_error)
    n_paths: int        # effective sample size (2x input n_paths with antithetic variates)


def price(
    inputs: ModelInputs,
    n_paths: int = 100_000,
    seed: Optional[int] = None,
) -> MCResult:
    """Price a European option by simulating terminal stock prices under GBM.

    Uses antithetic variates: for every drawn z, we also include -z, which
    cancels first-order Monte Carlo error and roughly doubles effective sample
    size. Pass a ``seed`` for reproducible results.
    """
    S, K, T = inputs.S, inputs.K, inputs.T
    r, sigma, q = inputs.r, inputs.sigma, inputs.q
    is_call = inputs.option_type == "call"

    if T <= 0:
        intrinsic = max(S - K, 0.0) if is_call else max(K - S, 0.0)
        return MCResult(price=intrinsic, std_error=0.0, n_paths=0)

    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths)
    z = np.concatenate([z, -z])  # antithetic variates

    drift = (r - q - 0.5 * sigma ** 2) * T
    diffusion = sigma * math.sqrt(T)
    ST = S * np.exp(drift + diffusion * z)

    payoffs = np.maximum(ST - K, 0.0) if is_call else np.maximum(K - ST, 0.0)
    discounted = math.exp(-r * T) * payoffs

    return MCResult(
        price=float(discounted.mean()),
        std_error=float(discounted.std(ddof=1) / math.sqrt(len(discounted))),
        n_paths=len(discounted),
    )
