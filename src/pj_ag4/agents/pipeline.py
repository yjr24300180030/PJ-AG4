"""
重构2：
pipeline——将各阶段串接成一次完整决策
RolePipelineAgent类定义了固定的四阶段执行顺序
子类通过构造函数注入不同的stage实现
"""

from dataclasses import replace
from typing import Any

from ..config import AgentConfig
from ..contracts import AgentAction, DecisionTrace, MarketObservation


class RolePipelineAgent:
    """
    pipeline基类，按 forecast → price → quantity → risk-gate 顺序执行。
    """

    def __init__(
        self,
        config: AgentConfig,
        *,
        forecaster: Any,
        pricer: Any,
        allocator: Any,
        risk_gate: Any,
        trace_source: str = "pipeline",
    ) -> None:
        self.config = config
        self._forecaster = forecaster
        self._pricer = pricer
        self._allocator = allocator
        self._risk_gate = risk_gate
        self._trace_source = trace_source

    def _stage_trace(self, stage: Any) -> dict[str, Any]:
        trace = getattr(stage, "last_trace", {})
        return trace if isinstance(trace, dict) else {}

    def _build_trace(
        self,
        *,
        reviewed_action: AgentAction,
        fallback: AgentAction | None,
    ) -> DecisionTrace:
        forecast_trace = self._stage_trace(self._forecaster)
        price_trace = self._stage_trace(self._pricer)
        quantity_trace = self._stage_trace(self._allocator)
        risk_trace = self._stage_trace(self._risk_gate)
        forecast_base = float(forecast_trace.get("base", reviewed_action.forecast_demand))
        forecast_adjustment = float(forecast_trace.get("adjustment", 0.0))
        price_base = float(price_trace.get("base", reviewed_action.price))
        price_adjustment = float(price_trace.get("adjustment", 0.0))
        quantity_target = float(quantity_trace.get("target", reviewed_action.quantity))
        risk_adjustment = str(risk_trace.get("adjustment", "none") or "none")
        llm_status = str(
            forecast_trace.get("llm_status")
            or price_trace.get("llm_status")
            or quantity_trace.get("llm_status")
            or ""
        )
        llm_prompt_excerpt = str(
            forecast_trace.get("llm_prompt_excerpt")
            or price_trace.get("llm_prompt_excerpt")
            or quantity_trace.get("llm_prompt_excerpt")
            or ""
        )
        llm_reasoning = str(
            forecast_trace.get("llm_reasoning")
            or price_trace.get("llm_reasoning")
            or quantity_trace.get("llm_reasoning")
            or ""
        )
        summary = (
            f"forecast {forecast_base:.1f} + {forecast_adjustment:.1f}; "
            f"price {price_base:.2f} + {price_adjustment:.2f}; "
            f"quantity target {quantity_target:.1f}; "
            f"risk gate {risk_adjustment}; "
            f"final forecast={reviewed_action.forecast_demand}, "
            f"price={reviewed_action.price:.2f}, quantity={reviewed_action.quantity}"
        )
        if llm_reasoning:
            summary += f" | reasoning: {llm_reasoning}"
        return DecisionTrace(
            source=self._trace_source,
            summary=summary,
            forecast_base=forecast_base,
            forecast_adjustment=forecast_adjustment,
            price_base=price_base,
            price_adjustment=price_adjustment,
            quantity_target=quantity_target,
            risk_gate_adjustment=risk_adjustment,
            final_forecast=reviewed_action.forecast_demand,
            final_price=reviewed_action.price,
            final_quantity=reviewed_action.quantity,
            fallback_used=False,
            llm_status=llm_status,
            llm_prompt_excerpt=llm_prompt_excerpt,
        )

    def _run_pipeline(
        self,
        observation: MarketObservation,
        *,
        fallback: AgentAction | None = None,
    ) -> AgentAction:
        """执行完整pipeline过程"""
        forecast = self._forecaster.run(observation, fallback=fallback)
        price = self._pricer.run(observation, forecast, fallback=fallback)
        quantity = self._allocator.run(observation, forecast, price, fallback=fallback)
        reviewed = self._risk_gate.review(
            observation,
            AgentAction(forecast_demand=forecast, price=price, quantity=quantity),
            fallback=fallback,
        )
        return replace(reviewed, trace=self._build_trace(reviewed_action=reviewed, fallback=fallback))

    def decide(self, observation: MarketObservation) -> AgentAction:
        """此为仿真环境调用的唯一公共入口。"""
        return self._run_pipeline(observation)
