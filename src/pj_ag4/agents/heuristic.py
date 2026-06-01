"""
重构2：
启发式pipeline——基于规则的需求预测、定价、分配
与 LLM 模式不同，完全由数学公式和style中设置的风格偏置驱动，不涉及外部 API。
"""

from typing import Callable

from ..config import AgentConfig
from ..contracts import AgentAction, MarketObservation
from ..utils import int_round_to_step, round_to_step, weighted_forecast
from .pipeline import RolePipelineAgent
from .risk import RiskGateStage
from .styles import allocator_style_adjustment, forecaster_style_adjustment, pricer_style_adjustment


# ── 管线各阶段 ──────────────────────────────────────────────

class HeuristicForecasterStage:
    """预测器：使用加权历史 + 风格偏置 + agent hook 产出需求预测。"""

    def __init__(
        self,
        adjust_fn: Callable[[MarketObservation, float], float],
        style: str,
    ) -> None:
        # adjust_fn 是 agent 的 hook 方法，传入观察 + 趋势返回调整值
        self._adjust_fn = adjust_fn
        self._style = style
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, *, fallback: AgentAction | None = None) -> int:
        del fallback
        history = observation.observed_demand_history
        trend = 0.0
        if not history:
            # 首回合无历史：直接使用当前观测值
            forecast = float(observation.observed_demand)
        else:
            base = weighted_forecast(history, short_window=3)
            forecast = 0.7 * base + 0.3 * history[-1]
        if len(history) >= 2:
            trend = (history[-1] - history[0]) / max(1, len(history) - 1)
        hook_adjustment = self._adjust_fn(observation, trend)
        style_adjustment = forecaster_style_adjustment(self._style, observation, trend)
        forecast += hook_adjustment + style_adjustment
        final_forecast = max(0, int(round(forecast)))
        self.last_trace = {
            "base": base if history else float(observation.observed_demand),
            "adjustment": hook_adjustment + style_adjustment,
            "hook_adjustment": hook_adjustment,
            "style_adjustment": style_adjustment,
            "trend": trend,
            "final": float(final_forecast),
        }
        return final_forecast


class HeuristicPricerStage:
    """定价器：基于 base_price + agent hook + 风格偏置 计算价格。"""

    def __init__(
        self,
        config: AgentConfig,
        adjust_fn: Callable[[MarketObservation, int], float],
        style: str,
    ) -> None:
        self._config = config
        self._adjust_fn = adjust_fn
        self._style = style
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, forecast: int, *, fallback: AgentAction | None = None) -> float:
        del fallback
        hook_adjustment = self._adjust_fn(observation, forecast)
        style_adjustment = pricer_style_adjustment(self._style, observation, forecast)
        value = self._config.base_price + hook_adjustment + style_adjustment
        final_price = round_to_step(value, self._config.price_step, self._config.price_floor, self._config.price_ceiling)
        self.last_trace = {
            "base": self._config.base_price,
            "adjustment": hook_adjustment + style_adjustment,
            "hook_adjustment": hook_adjustment,
            "style_adjustment": style_adjustment,
            "raw": value,
            "final": final_price,
        }
        return final_price


class HeuristicAllocatorStage:
    """分配器：基于 agent hook + 风格偏置 计算产能/库存增量。"""

    def __init__(
        self,
        config: AgentConfig,
        target_fn: Callable[[MarketObservation, int], float],
        style: str,
    ) -> None:
        self._config = config
        self._target_fn = target_fn
        self._style = style
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, forecast: int, price: float, *, fallback: AgentAction | None = None) -> int:
        del price, fallback
        target = self._target_fn(observation, forecast)
        style_adjustment = allocator_style_adjustment(self._style, observation, forecast)
        raw_target = target + style_adjustment
        final_quantity = int_round_to_step(raw_target, self._config.quantity_step, 0, self._config.max_quantity)
        self.last_trace = {
            "base": target,
            "adjustment": style_adjustment,
            "target": raw_target,
            "final": float(final_quantity),
        }
        return final_quantity


# ── Agent 类层次 ───────────────────────────────────────────

class HeuristicAgent(RolePipelineAgent):
    """启发式 agent 基类，无角色偏置。

    子类通过覆写三个 hook 方法实现角色差异化：
      - _forecast_adjustment(obs, trend) → 加到 forecast 上
      - _price_adjustment(obs, forecast) → 加到 base_price 上
      - _quantity_target(obs, forecast)  → 作为数量基础值
    """

    def __init__(self, config: AgentConfig) -> None:
        # 将子类覆写的 hook 方法作为 Callable 传给各 stage
        forecaster = HeuristicForecasterStage(self._forecast_adjustment, config.forecaster_style)
        pricer = HeuristicPricerStage(config, self._price_adjustment, config.pricer_style)
        allocator = HeuristicAllocatorStage(config, self._quantity_target, config.allocator_style)
        super().__init__(
            config,
            forecaster=forecaster,
            pricer=pricer,
            allocator=allocator,
            risk_gate=RiskGateStage(config),
            trace_source="heuristic",
        )

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        del observation, trend
        return 0.0

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del observation, forecast
        return 0.0

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        del observation
        return float(forecast)


class HyperscalerAgent(HeuristicAgent):
    """规模主导型——激进定价、高产能、增长容忍"""

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.25 * trend + 0.15 * max(0.0, observation.own_last_shortage)

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        inventory_pressure = max(0.0, 35.0 - observation.own_inventory) / 100.0
        competition_discount = max(0.0, 0.25 - observation.own_reputation) * 0.5
        return -0.35 + 0.05 * inventory_pressure - competition_discount - 0.01 * observation.market_volatility

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        urgency = max(0.0, forecast - observation.own_inventory)
        return forecast * 0.95 + urgency * 0.35 + max(0.0, 20.0 - observation.own_inventory)


class PremiumCloudAgent(HeuristicAgent):
    """SLA优先型——高价位、声誉溢价、保守产能"""

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.15 * trend + 0.05 * observation.own_reputation

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        reputation_premium = 0.55 + 0.35 * observation.own_reputation
        volatility_premium = 0.04 * observation.market_volatility
        return reputation_premium + volatility_premium

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return forecast * 0.72 + max(0.0, 12.0 - observation.own_inventory) * 0.3


class SpotBrokerAgent(HeuristicAgent):
    """波动型——轻库存、反应快、灵活机动"""

    def _forecast_adjustment(self, observation: MarketObservation, trend: float) -> float:
        return 0.45 * trend + 0.08 * observation.market_volatility

    def _price_adjustment(self, observation: MarketObservation, forecast: int) -> float:
        del forecast
        inventory_pressure = max(0.0, observation.own_inventory - 15.0) / 120.0
        trend_discount = -0.08 * max(0.0, observation.own_last_shortage)
        return 0.08 - 0.28 * inventory_pressure + trend_discount

    def _quantity_target(self, observation: MarketObservation, forecast: int) -> float:
        return forecast * 0.58 + observation.market_volatility * 0.8 + max(0.0, 10.0 - observation.own_inventory) * 0.5
