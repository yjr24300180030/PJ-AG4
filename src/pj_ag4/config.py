from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from pathlib import Path
from typing import Sequence

from dotenv import find_dotenv, load_dotenv

# 默认内置JSON文档路径
_DEFAULT_AGENTS_FILE = Path(__file__).resolve().parent / "data" / "agents.json"


def _load_runtime_env() -> None:
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)
        return
    repo_root_env = Path(__file__).resolve().parents[2] / ".env"
    if repo_root_env.exists():
        load_dotenv(dotenv_path=repo_root_env, override=False)


@dataclass(frozen=True)
class CustomerSegmentConfig:
    name: str
    demand_fraction: float
    price_weight: float
    reputation_weight: float
    brand_weight: float
    sla_weight: float
    role_bias: dict[str, float] = field(default_factory=dict)
    contract_fraction: float = 0.0


def _default_customer_segments() -> tuple[CustomerSegmentConfig, ...]:
    return (
        CustomerSegmentConfig(
            name="training_burst",
            demand_fraction=0.45,
            price_weight=0.75,
            reputation_weight=0.8,
            brand_weight=1.0,
            sla_weight=0.35,
            role_bias={"hyperscaler": 0.35, "premium": 0.05, "spot": 0.05},
            contract_fraction=0.10,
        ),
        CustomerSegmentConfig(
            name="enterprise_sla",
            demand_fraction=0.35,
            price_weight=0.35,
            reputation_weight=1.45,
            brand_weight=1.0,
            sla_weight=1.10,
            role_bias={"hyperscaler": 0.05, "premium": 0.45, "spot": -0.15},
            contract_fraction=0.75,
        ),
        CustomerSegmentConfig(
            name="spot_workload",
            demand_fraction=0.20,
            price_weight=1.15,
            reputation_weight=0.45,
            brand_weight=0.75,
            sla_weight=0.15,
            role_bias={"hyperscaler": -0.05, "premium": -0.10, "spot": 0.50},
            contract_fraction=0.05,
        ),
    )


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
    reputation_delivery_weight: float = 0.5
    reputation_pricing_weight: float = 0.3
    reputation_cooperation_weight: float = 0.2
    price_weight: float = 0.7
    cooperation_alpha0: float = -0.8
    cooperation_alpha1: float = 2.5
    cooperation_alpha2: float = 1.2
    cooperation_alpha3: float = 1.5
    indirect_reciprocity_alpha: float = 0.1
    transfer_markup: float = 0.05
    max_transfer: float = 15.0
    reputation_update_rate: float = 0.25
    demand_window: int = 5
    customer_segments: tuple[CustomerSegmentConfig, ...] = field(default_factory=_default_customer_segments)
    reallocation_enabled: bool = True
    reallocation_fill_rate: float = 1.0
    transfer_enabled: bool = True
    sla_queue_enabled: bool = True
    sla_backlog_penalty_multiplier: float = 0.75
    price_pressure_cost_rate: float = 0.0


@dataclass(frozen=True)
class AgentConfig:
    name: str
    role: str
    persona: str
    forecaster_style: str
    pricer_style: str
    allocator_style: str
    risk_style: str
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
    obsolescence_rate: float
    obsolescence_penalty: float
    sla_penalty: float
    menu_cost_rate: float


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = "http://127.0.0.1:8045/v1"
    api_key: str | None = None
    model: str = "gemini-3-flash"
    temperature: float = 0.0
    max_tokens: int = 512
    max_retries: int = 1
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = 7
    rounds: int = 30
    output_dir: Path = Path("outputs")
    agent_mode: str = "heuristic"
    scenario: str = "baseline"
    market: MarketConfig = field(default_factory=MarketConfig)
    llm: LLMConfig | None = None
    agents: tuple[AgentConfig, ...] = field(default_factory=tuple)




def load_agent_configs(
    profile: str = "default",
    *,
    source: str | Path | None = None,
) -> tuple[AgentConfig, ...]:
    """重构1：去除原有default_simulation_config里的agent config构造，
    将agent配置独立为一个JSON文档进行加载
    并新增读取JSON文件的API。
    
    暂时保持原有的函数式编程和annotations风格

    参数:
        profile: 要加载的agent配置集的名称，默认为"default"
        source: JSON文件路径，None时使用默认内置JSON文档
    """
    path = Path(source) if source is not None else _DEFAULT_AGENTS_FILE
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    profile_data = data.get("profiles", {}).get(profile)
    if profile_data is None:
        known = ", ".join(sorted(data.get("profiles", {})))
        raise ValueError(
            f"unknown agent profile {profile!r}; "
            f"available profiles: {known or '(none)'}"
        )
    return tuple(AgentConfig(**entry) for entry in profile_data)


def _normalize_segments(segments: tuple[CustomerSegmentConfig, ...]) -> tuple[CustomerSegmentConfig, ...]:
    total = sum(max(0.0, segment.demand_fraction) for segment in segments)
    if total <= 0:
        return _default_customer_segments()
    return tuple(
        CustomerSegmentConfig(
            name=segment.name,
            demand_fraction=max(0.0, segment.demand_fraction) / total,
            price_weight=segment.price_weight,
            reputation_weight=segment.reputation_weight,
            brand_weight=segment.brand_weight,
            sla_weight=segment.sla_weight,
            role_bias=dict(segment.role_bias),
            contract_fraction=segment.contract_fraction,
        )
        for segment in segments
    )


def _market_for_scenario(scenario: str, market: MarketConfig) -> MarketConfig:
    scenario_key = scenario.replace("-", "_").lower()
    if scenario_key == "baseline":
        return market
    if scenario_key == "price_war":
        return replace(
            market,
            price_weight=1.15,
            reputation_weight=0.85,
            transfer_markup=0.02,
            price_pressure_cost_rate=0.55,
            reallocation_enabled=True,
            transfer_enabled=True,
            customer_segments=_normalize_segments(
                (
                    CustomerSegmentConfig("training_burst", 0.38, 1.05, 0.55, 0.95, 0.20, {"hyperscaler": 0.30}),
                    CustomerSegmentConfig("enterprise_sla", 0.22, 0.50, 1.15, 1.0, 0.95, {"premium": 0.45}, 0.8),
                    CustomerSegmentConfig("spot_workload", 0.40, 1.70, 0.20, 0.65, 0.05, {"spot": 0.65}),
                )
            ),
        )
    if scenario_key == "supply_shock":
        return replace(
            market,
            shock_round=8,
            shock_magnitude=60.0,
            ar_sigma=9.0,
            max_transfer=35.0,
            transfer_markup=0.04,
            cooperation_alpha0=0.25,
            reallocation_fill_rate=0.60,
            transfer_enabled=True,
            sla_queue_enabled=True,
        )
    if scenario_key == "high_volatility":
        return replace(
            market,
            ar_sigma=16.0,
            observation_noise_sigma=10.0,
            seasonal_amplitude_7=25.0,
            shock_round=12,
            shock_magnitude=35.0,
            sla_queue_enabled=True,
        )
    if scenario_key == "no_reputation":
        return replace(
            market,
            reputation_weight=0.0,
            reputation_delivery_weight=0.0,
            reputation_pricing_weight=0.0,
            reputation_cooperation_weight=0.0,
            customer_segments=_normalize_segments(
                tuple(
                    CustomerSegmentConfig(
                        name=segment.name,
                        demand_fraction=segment.demand_fraction,
                        price_weight=segment.price_weight,
                        reputation_weight=0.0,
                        brand_weight=segment.brand_weight,
                        sla_weight=0.0,
                        role_bias=segment.role_bias,
                        contract_fraction=segment.contract_fraction,
                    )
                    for segment in market.customer_segments
                )
            ),
        )
    if scenario_key == "no_transfer":
        return replace(market, transfer_enabled=False, max_transfer=0.0)
    raise ValueError(
        "unknown scenario "
        f"{scenario!r}; available scenarios: baseline, price_war, supply_shock, high_volatility, no_reputation, no_transfer"
    )


def default_simulation_config(
    *,
    seed: int = 7,
    rounds: int = 30,
    output_dir: str | Path = "outputs",
    agent_mode: str = "heuristic",
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    agents_profile: str = "default",
    agents_file: str | Path | None = None,
    scenario: str = "baseline",
) -> SimulationConfig:
    _load_runtime_env()
    agents = load_agent_configs(agents_profile, source=agents_file)
    resolved_llm_api_key = llm_api_key or os.getenv("PJ_AG4_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_config = LLMConfig(
        base_url=llm_base_url or os.getenv("PJ_AG4_OPENAI_BASE_URL") or "http://127.0.0.1:8045/v1",
        api_key=resolved_llm_api_key,
        model=llm_model or os.getenv("PJ_AG4_OPENAI_MODEL") or "gemini-3-flash",
    )
    market = _market_for_scenario(scenario, MarketConfig())
    return SimulationConfig(
        seed=seed,
        rounds=rounds,
        output_dir=Path(output_dir),
        agent_mode=agent_mode,
        scenario=scenario,
        market=market,
        llm=llm_config,
        agents=agents,
    )
