"""Stochastic simulation utilities."""

from __future__ import annotations

import math
import random


def poisson(lam: float) -> int:
    """Sample from Poisson distribution.

    Uses Knuth algorithm for small lambda, normal approximation for large.
    """
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, round(random.gauss(lam, math.sqrt(lam))))
    exp_neg_lam = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p < exp_neg_lam:
            return k - 1


def michaelis_menten(substrate: float, vmax: float, km: float) -> float:
    """Michaelis-Menten kinetics: v = Vmax * S / (Km + S)."""
    if substrate <= 0 or vmax <= 0:
        return 0.0
    return vmax * substrate / (km + substrate)


def hill(x: float, k: float, n: float = 2.0) -> float:
    """Hill function for cooperative binding: x^n / (K^n + x^n)."""
    if x <= 0 or k <= 0:
        return 0.0
    xn = x ** n
    return xn / (k ** n + xn)
