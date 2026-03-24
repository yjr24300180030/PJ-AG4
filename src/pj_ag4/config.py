from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MarketConfig:
    demand_base: float = 180.0
    demand_growth: float = 0.6
    seasonal_amplitude_7: float = 18.0
    seasonal_amplitude_30: float = 10.0
    seasonal_phase: float = 0.3
    shock_round: int = 35
    shock_magnitude: float = -20.0
    ar_rho: float = 0.45
    ar_sigma: float = 7.0
    observation_noise_sigma: float = 5.0
    demand_floor: int = 50
    reputation_weight: float = 1.2
    price_weight: float = 0.7
    cooperation_alpha0: float = -0.8
    cooperation_alpha1: float = 2.5
    cooperation_alpha2: float = 1.2
    cooperation_alpha3: float = 1.5
    transfer_markup: float = 0.05
    max_transfer: float = 15.0
    reputation_update_rate: float = 0.25
    demand_window: int = 5


@dataclass(frozen=True)
class AgentConfig:
    name: str
    role: str
    base_price: float
    price_floor: float
    price_ceiling: float
    price_step: float
    quantity_step: int
    max_quantity: int
    inventory_start: float
    reputation_start: float
    brand_strength: float
    linear_cost: float
    quadratic_cost: float
    holding_cost_rate: float
    obsolescence_penalty: float
    sla_penalty: float
    menu_cost_rate: float


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 7
    rounds: int = 30
    output_dir: Path = Path("outputs")
    market: MarketConfig = field(default_factory=MarketConfig)
    agents: tuple[AgentConfig, ...] = field(default_factory=tuple)


def default_simulation_config(*, seed: int = 7, rounds: int = 30, output_dir: str | Path = "outputs") -> SimulationConfig:
    agents = (
        AgentConfig(
            name="Hyperscaler",
            role="hyperscaler",
            base_price=4.6,
            price_floor=4.0,
            price_ceiling=6.0,
            price_step=0.2,
            quantity_step=10,
            max_quantity=120,
            inventory_start=30.0,
            reputation_start=0.65,
            brand_strength=0.05,
            linear_cost=3.0,
            quadratic_cost=0.015,
            holding_cost_rate=0.10,
            obsolescence_penalty=0.25,
            sla_penalty=1.20,
            menu_cost_rate=0.02,
        ),
        AgentConfig(
            name="PremiumCloud",
            role="premium",
            base_price=5.4,
            price_floor=4.4,
            price_ceiling=7.0,
            price_step=0.2,
            quantity_step=10,
            max_quantity=100,
            inventory_start=20.0,
            reputation_start=0.80,
            brand_strength=0.30,
            linear_cost=3.4,
            quadratic_cost=0.010,
            holding_cost_rate=0.08,
            obsolescence_penalty=0.20,
            sla_penalty=1.50,
            menu_cost_rate=0.02,
        ),
        AgentConfig(
            name="SpotBroker",
            role="spot",
            base_price=4.9,
            price_floor=3.8,
            price_ceiling=6.4,
            price_step=0.2,
            quantity_step=10,
            max_quantity=80,
            inventory_start=15.0,
            reputation_start=0.55,
            brand_strength=0.10,
            linear_cost=3.6,
            quadratic_cost=0.008,
            holding_cost_rate=0.12,
            obsolescence_penalty=0.22,
            sla_penalty=1.30,
            menu_cost_rate=0.03,
        ),
    )
    return SimulationConfig(
        seed=seed,
        rounds=rounds,
        output_dir=Path(output_dir),
        agents=agents,
    )

