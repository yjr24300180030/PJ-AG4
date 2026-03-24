from __future__ import annotations

import math
from statistics import mean
from typing import Iterable, Sequence


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def stable_softmax(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    peak = max(values)
    exps = [math.exp(value - peak) for value in values]
    total = sum(exps)
    if total == 0:
        return [1.0 / len(values)] * len(values)
    return [value / total for value in exps]


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def round_to_step(value: float, step: float, minimum: float, maximum: float) -> float:
    if step <= 0:
        raise ValueError("step must be positive")
    snapped = round(value / step) * step
    return clamp(round(snapped, 10), minimum, maximum)


def int_round_to_step(value: float, step: int, minimum: int, maximum: int) -> int:
    if step <= 0:
        raise ValueError("step must be positive")
    snapped = int(round(value / step) * step)
    return int(clamp(snapped, minimum, maximum))


def rolling_mean(values: Sequence[float], window: int | None = None) -> float:
    if not values:
        return 0.0
    subset = values[-window:] if window and window > 0 else values
    return mean(subset)


def rolling_volatility(values: Sequence[float], window: int | None = None) -> float:
    subset = values[-window:] if window and window > 0 else values
    if len(subset) <= 1:
        return 0.0
    mu = mean(subset)
    return math.sqrt(sum((value - mu) ** 2 for value in subset) / len(subset))


def weighted_forecast(history: Sequence[int], short_window: int = 3) -> float:
    if not history:
        return 0.0
    if len(history) == 1:
        return float(history[-1])
    window = list(history[-short_window:])
    weights = list(range(1, len(window) + 1))
    numerator = sum(value * weight for value, weight in zip(window, weights, strict=True))
    denominator = sum(weights)
    return numerator / denominator if denominator else float(window[-1])

