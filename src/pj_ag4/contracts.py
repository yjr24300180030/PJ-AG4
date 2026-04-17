from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentAction:
    forecast_demand: int
    price: float
    quantity: int


@dataclass(frozen=True)
class MarketObservation:
    round_index: int
    observed_demand: int
    demand_history: tuple[int, ...]
    observed_demand_history: tuple[int, ...]
    price_history: tuple[tuple[float, ...], ...]
    reputation_history: tuple[tuple[float, ...], ...]
    peer_reputations: tuple[tuple[str, float], ...]
    own_inventory: float
    own_last_profit: float
    own_last_shortage: float
    own_reputation: float
    market_avg_price: float
    market_volatility: float


@dataclass(frozen=True)
class SimulationResult:
    rows: list[object]
    csv_path: Path
    figure_path: Path | None
    dashboard_path: Path | None = None
