"""
重构3：
将SettlementRow类移入contracts模块。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


def _unit_interval(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _adaptive_interval(value: Any) -> float:
    return max(0.05, min(0.95, _unit_interval(value)))


def _float_dict(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    values: dict[str, float] = {}
    for key, item in value.items():
        try:
            values[str(key)] = float(item)
        except (TypeError, ValueError):
            values[str(key)] = 0.0
    return values


@dataclass(frozen=True)
class DecisionTrace:
    source: str
    summary: str
    forecast_base: float = 0.0
    forecast_adjustment: float = 0.0
    price_base: float = 0.0
    price_adjustment: float = 0.0
    quantity_target: float = 0.0
    risk_gate_adjustment: str = "none"
    final_forecast: int = 0
    final_price: float = 0.0
    final_quantity: int = 0
    fallback_used: bool = False
    llm_status: str = ""
    llm_error: str = ""
    llm_prompt_excerpt: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str | None) -> "DecisionTrace | None":
        if not value:
            return None
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return cls(**{key: payload.get(key) for key in cls.__dataclass_fields__})

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyState:
    risk_tolerance: float = 0.5
    price_aggressiveness: float = 0.5
    demand_sensitivity: float = 0.5
    inventory_caution: float = 0.5
    shock_responsiveness: float = 0.5
    competitor_reactivity: float = 0.5

    @classmethod
    def from_role(cls, role: str) -> "StrategyState":
        if role == "hyperscaler":
            return cls(
                risk_tolerance=0.72,
                price_aggressiveness=0.68,
                demand_sensitivity=0.62,
                inventory_caution=0.34,
                shock_responsiveness=0.48,
                competitor_reactivity=0.46,
            )
        if role == "premium":
            return cls(
                risk_tolerance=0.38,
                price_aggressiveness=0.58,
                demand_sensitivity=0.46,
                inventory_caution=0.72,
                shock_responsiveness=0.36,
                competitor_reactivity=0.32,
            )
        if role == "spot":
            return cls(
                risk_tolerance=0.56,
                price_aggressiveness=0.44,
                demand_sensitivity=0.58,
                inventory_caution=0.54,
                shock_responsiveness=0.76,
                competitor_reactivity=0.78,
            )
        return cls()

    @classmethod
    def fields(cls) -> tuple[str, ...]:
        return tuple(cls.__dataclass_fields__)

    def bounded(self) -> "StrategyState":
        return StrategyState(**{field: _unit_interval(getattr(self, field)) for field in self.fields()})

    def apply_delta(self, delta: dict[str, float]) -> "StrategyState":
        values = {
            field: _adaptive_interval(getattr(self, field) + float(delta.get(field, 0.0)))
            for field in self.fields()
        }
        return StrategyState(**values)

    def to_json(self) -> str:
        return json.dumps(asdict(self.bounded()), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str | None) -> "StrategyState | None":
        if not value:
            return None
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        return cls(**{field: _unit_interval(payload.get(field, 0.5)) for field in cls.fields()})

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self.bounded())


@dataclass(frozen=True)
class StrategyPersonality:
    label: str
    objective_bias: str
    prompt_guidance: str
    delta_weights: dict[str, float]
    max_delta_by_param: dict[str, float]

    @classmethod
    def from_role(cls, role: str) -> "StrategyPersonality":
        fields = StrategyState.fields()
        if role == "hyperscaler":
            return cls(
                label="Scale aggressor",
                objective_bias="Market share and continuity first; tolerate measured inventory risk.",
                prompt_guidance=(
                    "Prefer share capture, capacity readiness, and fast recovery from shortages. "
                    "Do not become overly premium or inventory-light after one weak round."
                ),
                delta_weights={
                    "risk_tolerance": 1.2,
                    "price_aggressiveness": 1.15,
                    "demand_sensitivity": 1.05,
                    "inventory_caution": 0.75,
                    "shock_responsiveness": 0.9,
                    "competitor_reactivity": 0.85,
                },
                max_delta_by_param={field: 0.10 for field in fields},
            )
        if role == "premium":
            return cls(
                label="Reputation guardian",
                objective_bias="Reputation, service stability, and premium discipline first.",
                prompt_guidance=(
                    "Preserve price discipline and SLA reliability. Avoid overreacting to one round "
                    "of lost share if reputation and service remain strong."
                ),
                delta_weights={
                    "risk_tolerance": 0.65,
                    "price_aggressiveness": 0.75,
                    "demand_sensitivity": 0.85,
                    "inventory_caution": 1.2,
                    "shock_responsiveness": 0.75,
                    "competitor_reactivity": 0.55,
                },
                max_delta_by_param={field: 0.08 for field in fields},
            )
        if role == "spot":
            return cls(
                label="Agile spread hunter",
                objective_bias="Fast reaction, tactical price following, and shock exploitation first.",
                prompt_guidance=(
                    "React quickly to competitor price gaps and demand shocks. Stay flexible and "
                    "avoid locking into large inventory commitments."
                ),
                delta_weights={
                    "risk_tolerance": 0.9,
                    "price_aggressiveness": 0.9,
                    "demand_sensitivity": 1.0,
                    "inventory_caution": 1.0,
                    "shock_responsiveness": 1.25,
                    "competitor_reactivity": 1.25,
                },
                max_delta_by_param={field: 0.10 for field in fields},
            )
        return cls(
            label="Balanced learner",
            objective_bias="Balanced profit, service, and market position.",
            prompt_guidance="Update strategy gradually and keep a balanced market posture.",
            delta_weights={field: 1.0 for field in fields},
            max_delta_by_param={field: 0.10 for field in fields},
        )

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyUpdateTrace:
    source: str
    personality_label: str
    previous_state: StrategyState
    raw_delta: dict[str, float]
    bounded_delta: dict[str, float]
    new_state: StrategyState
    reason: str
    feedback_summary: str
    fallback_used: bool = False
    llm_status: str = ""
    llm_error: str = ""
    llm_prompt_excerpt: str = ""

    def to_json(self) -> str:
        return json.dumps(self.to_public_dict(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str | None) -> "StrategyUpdateTrace | None":
        if not value:
            return None
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        previous_payload = payload.get("previous_state", {})
        new_payload = payload.get("new_state", {})
        previous_state = StrategyState.from_json(json.dumps(previous_payload)) or StrategyState()
        new_state = StrategyState.from_json(json.dumps(new_payload)) or StrategyState()
        return cls(
            source=str(payload.get("source", "")),
            personality_label=str(payload.get("personality_label", "")),
            previous_state=previous_state,
            raw_delta=_float_dict(payload.get("raw_delta", {})),
            bounded_delta=_float_dict(payload.get("bounded_delta", {})),
            new_state=new_state,
            reason=str(payload.get("reason", "")),
            feedback_summary=str(payload.get("feedback_summary", "")),
            fallback_used=bool(payload.get("fallback_used", False)),
            llm_status=str(payload.get("llm_status", "")),
            llm_error=str(payload.get("llm_error", "")),
            llm_prompt_excerpt=str(payload.get("llm_prompt_excerpt", "")),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "personality_label": self.personality_label,
            "previous_state": self.previous_state.to_public_dict(),
            "raw_delta": dict(self.raw_delta),
            "bounded_delta": dict(self.bounded_delta),
            "new_state": self.new_state.to_public_dict(),
            "reason": self.reason,
            "feedback_summary": self.feedback_summary,
            "fallback_used": self.fallback_used,
            "llm_status": self.llm_status,
            "llm_error": self.llm_error,
            "llm_prompt_excerpt": self.llm_prompt_excerpt,
        }


@dataclass(frozen=True)
class AgentAction:
    forecast_demand: int
    price: float
    quantity: int
    trace: DecisionTrace | None = None
    strategy_state: StrategyState | None = None
    strategy_update_trace: StrategyUpdateTrace | None = None


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
class SettlementRow:
    """单回合、单agent的完整字段记录"""
    seed: int
    round: int
    agent_name: str
    agent_role: str
    agent_action: str
    decision_source: str
    decision_reason: str
    decision_trace: str
    strategy_state: str
    strategy_update_reason: str
    strategy_update_trace: str
    forecast_demand: int
    forecast_error_abs: float
    forecast_error_sq: float
    demand_true: int
    demand_obs: int
    trend_component: float
    season_component: float
    shock_component: float
    noise_component: float
    market_avg_price: float
    market_total_sales: float
    inventory_start: float
    reputation_start: float
    rep_delivery_start: float
    rep_pricing_start: float
    rep_cooperation_start: float
    price: float
    quantity: int
    available_supply: float
    attractiveness: float
    demand_share: float
    allocated_demand: float
    shortage_pre_transfer: float
    surplus_pre_transfer: float
    transfer_in: float
    transfer_out: float
    transfer_cost: float
    transfer_revenue: float
    transfer_attempts: int
    transfer_accepts: int
    coop_probability: float
    coop_accept_rate: float
    segment_demand: str
    segment_allocations: str
    reallocated_in: float
    reallocated_out: float
    realized_sales: float
    shortage_post_transfer: float
    backlog_start: float
    new_contract_demand: float
    delivered_backlog: float
    backlog_end: float
    late_units: float
    sla_queue_penalty: float
    inventory_end: float
    obsolescence_units: float
    revenue: float
    prod_cost: float
    holding_cost: float
    obsolescence_cost: float
    sla_penalty: float
    price_pressure_cost: float
    menu_cost: float
    profit: float
    cum_profit: float
    service_rate: float
    help_ratio: float
    dump_flag: int
    default_flag: int
    rep_delivery_end: float
    rep_pricing_end: float
    rep_cooperation_end: float
    reputation_end: float


@dataclass(frozen=True)
class RoundTrace:
    round_index: int
    demand_true: float
    demand_observed: float
    market_total_sales: float
    market_avg_price: float
    transfer_volume: float
    default_count: int
    dump_count: int
    backlog_total: float
    summary: str

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimulationResult:
    rows: list[object]
    csv_path: Path
    figure_path: Path | None
    dashboard_path: Path | None = None
    report_path: Path | None = None
