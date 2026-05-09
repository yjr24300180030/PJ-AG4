from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .config import MarketConfig
from .utils import clamp


@dataclass(frozen=True)
class DemandSnapshot:
    round_index: int
    true_demand: int
    observed_demand: int
    trend_component: float
    seasonal_component: float
    shock_component: float
    noise_component: float


class DemandSeriesGenerator:
    def __init__(self, config: MarketConfig, seed: int) -> None:
        self._config = config
        self._rng = random.Random(seed)
        self._prev_noise = 0.0

    def step(self, round_index: int) -> DemandSnapshot:
        cfg = self._config
        trend = cfg.demand_base + cfg.demand_growth * round_index
        seasonal = (
            cfg.seasonal_amplitude_7 * math.sin(2 * math.pi * round_index / 7.0)
            + cfg.seasonal_amplitude_30 * math.sin(2 * math.pi * round_index / 30.0 + cfg.seasonal_phase)
        )
        shock = cfg.shock_magnitude if round_index >= cfg.shock_round else 0.0
        noise = cfg.ar_rho * self._prev_noise + self._rng.gauss(0.0, cfg.ar_sigma)
        self._prev_noise = noise

        true_demand = int(round(max(cfg.demand_floor, trend + seasonal + shock + noise)))
        observed_noise = self._rng.gauss(0.0, cfg.observation_noise_sigma)
        observed_demand = int(round(max(cfg.demand_floor, true_demand + observed_noise)))
        return DemandSnapshot(
            round_index=round_index,
            true_demand=true_demand,
            observed_demand=observed_demand,
            trend_component=trend,
            seasonal_component=seasonal,
            shock_component=shock,
            noise_component=noise,
        )

