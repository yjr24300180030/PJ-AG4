from __future__ import annotations

from pj_ag4.config import MarketConfig
from pj_ag4.timeseries import DemandSeriesGenerator


def test_demand_series_is_deterministic_and_positive() -> None:
    config = MarketConfig()
    series_a = DemandSeriesGenerator(config, seed=123)
    series_b = DemandSeriesGenerator(config, seed=123)

    values_a = [series_a.step(index).true_demand for index in range(6)]
    values_b = [series_b.step(index).true_demand for index in range(6)]

    assert values_a == values_b
    assert all(value >= config.demand_floor for value in values_a)

