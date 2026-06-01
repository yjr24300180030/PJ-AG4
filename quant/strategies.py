from __future__ import annotations

from pathlib import Path
import sys


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    src_root_str = str(repo_root / "src")
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_repo_root_on_path()

from pj_ag4.agents import HeuristicAgent, ensure_builtin_strategies_registered  # noqa: E402
from pj_ag4.config import AgentConfig, LLMConfig, SimulationConfig  # noqa: E402
from pj_ag4.strategy_registry import build_registered_agents, has_strategy, register_strategy, strategy_title as core_strategy_title  # noqa: E402


STRATEGY_HEURISTIC = "heuristic"
STRATEGY_LLM = "llm"
STRATEGY_RULE_PRICE_CUTTER = "rule_price_cutter"
STRATEGY_RULE_INVENTORY_GUARD = "rule_inventory_guard"

DEFAULT_STRATEGIES = (
    STRATEGY_HEURISTIC,
    STRATEGY_LLM,
    STRATEGY_RULE_PRICE_CUTTER,
    STRATEGY_RULE_INVENTORY_GUARD,
)


class RulePriceCutterAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation, trend: float) -> float:
        return 0.30 * trend + 0.05 * observation.market_volatility

    def _price_adjustment(self, observation, forecast: int) -> float:
        del forecast
        shortage_pressure = max(0.0, observation.own_last_shortage) / 100.0
        inventory_pressure = max(0.0, observation.own_inventory - 10.0) / 120.0
        role_bias = {"hyperscaler": -0.30, "premium": -0.20, "spot": -0.42}.get(self.config.role, -0.25)
        return role_bias - 0.25 * inventory_pressure - 0.18 * shortage_pressure - 0.02 * observation.market_volatility

    def _quantity_target(self, observation, forecast: int) -> float:
        return forecast * 1.00 + max(0.0, forecast - observation.own_inventory) * 0.35


class RuleInventoryGuardAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation, trend: float) -> float:
        return 0.18 * trend + 0.03 * observation.own_reputation

    def _price_adjustment(self, observation, forecast: int) -> float:
        del forecast
        inventory_excess = max(0.0, observation.own_inventory - 15.0) / 100.0
        role_bias = {"hyperscaler": -0.04, "premium": 0.20, "spot": 0.00}.get(self.config.role, 0.0)
        return 0.22 + role_bias + 0.30 * observation.own_reputation + 0.02 * observation.market_volatility - 0.12 * inventory_excess

    def _quantity_target(self, observation, forecast: int) -> float:
        inventory_buffer = max(0.0, 12.0 - observation.own_inventory)
        return forecast * 0.72 + 0.25 * inventory_buffer


def _build_rule_agents(
    configs: tuple[AgentConfig, ...],
    agent_cls: type[HeuristicAgent],
) -> dict[str, HeuristicAgent]:
    return {cfg.name: agent_cls(cfg) for cfg in configs}


_REGISTERED = False


def ensure_quant_strategies_registered() -> None:
    global _REGISTERED
    ensure_builtin_strategies_registered()
    if _REGISTERED and has_strategy(STRATEGY_RULE_PRICE_CUTTER) and has_strategy(STRATEGY_RULE_INVENTORY_GUARD):
        return
    register_strategy(
        STRATEGY_RULE_PRICE_CUTTER,
        title="Rule Price Cutter",
        builder=lambda configs, llm_config=None: _build_rule_agents(tuple(configs), RulePriceCutterAgent),
        replace=True,
    )
    register_strategy(
        STRATEGY_RULE_INVENTORY_GUARD,
        title="Rule Inventory Guard",
        builder=lambda configs, llm_config=None: _build_rule_agents(tuple(configs), RuleInventoryGuardAgent),
        replace=True,
    )
    _REGISTERED = True


def available_strategies() -> tuple[str, ...]:
    ensure_quant_strategies_registered()
    return DEFAULT_STRATEGIES


def strategy_title(strategy_name: str) -> str:
    ensure_quant_strategies_registered()
    return core_strategy_title(strategy_name)


def build_strategy_agents(
    strategy_name: str,
    config: SimulationConfig,
    *,
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    ensure_quant_strategies_registered()
    return build_registered_agents(strategy_name, config.agents, llm_config=llm_config)
