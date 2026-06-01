from __future__ import annotations

import json
from dataclasses import replace
from statistics import mean
from typing import Any, Sequence

from ..config import AgentConfig, LLMConfig
from ..contracts import (
    AgentAction,
    DecisionTrace,
    MarketObservation,
    SettlementRow,
    StrategyPersonality,
    StrategyState,
    StrategyUpdateTrace,
)
from ..providers import query_json_completion
from ..utils import clamp, int_round_to_step, round_to_step
from .pipeline import RolePipelineAgent
from .risk import RiskGateStage


class AdaptiveLLMAgent:
    """LLM-guided bounded strategy learner.

    The LLM updates strategy parameters after settlement; hard market actions
    remain bounded by deterministic transforms and the shared risk gate.
    """

    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        fallback_agent: RolePipelineAgent,
        client: Any,
    ) -> None:
        self.config = config
        self._llm_config = llm_config
        self._client = client
        self._fallback_agent = fallback_agent
        self._risk_gate = RiskGateStage(config)
        self._state = StrategyState.from_role(config.role).bounded()
        self._personality = StrategyPersonality.from_role(config.role)
        self._last_update_trace: StrategyUpdateTrace | None = None
        self._last_prompt_excerpt = ""

    @property
    def strategy_state(self) -> StrategyState:
        return self._state

    @property
    def personality(self) -> StrategyPersonality:
        return self._personality

    def decide(self, observation: MarketObservation) -> AgentAction:
        fallback = self._fallback_agent.decide(observation)
        adjusted = self._apply_strategy(observation, fallback)
        reviewed = self._risk_gate.review(observation, adjusted, fallback=fallback)
        trace = self._build_decision_trace(
            observation=observation,
            fallback=fallback,
            adjusted=adjusted,
            reviewed=reviewed,
        )
        return replace(
            reviewed,
            trace=trace,
            strategy_state=self._state,
            strategy_update_trace=self._last_update_trace,
        )

    def observe_result(
        self,
        row: SettlementRow,
        round_rows: Sequence[SettlementRow],
    ) -> StrategyUpdateTrace:
        previous_state = self._state
        try:
            raw_delta, reason = self._query_strategy_delta(row, round_rows)
            bounded_delta = self._bound_delta(raw_delta, previous_state)
            next_state = previous_state.apply_delta(bounded_delta)
            trace = StrategyUpdateTrace(
                source="llm-adaptive",
                personality_label=self._personality.label,
                previous_state=previous_state,
                raw_delta=raw_delta,
                bounded_delta=bounded_delta,
                new_state=next_state,
                reason=reason,
                feedback_summary=self._feedback_summary(row, round_rows),
                fallback_used=False,
                llm_status="ok",
                llm_prompt_excerpt=self._last_prompt_excerpt,
            )
        except Exception as exc:
            raw_delta = self._fallback_delta(row, round_rows)
            bounded_delta = self._bound_delta(raw_delta, previous_state)
            next_state = previous_state.apply_delta(bounded_delta)
            trace = StrategyUpdateTrace(
                source="llm-adaptive-fallback",
                personality_label=self._personality.label,
                previous_state=previous_state,
                raw_delta=raw_delta,
                bounded_delta=bounded_delta,
                new_state=next_state,
                reason=self._fallback_reason(row),
                feedback_summary=self._feedback_summary(row, round_rows),
                fallback_used=True,
                llm_status="fallback",
                llm_error=str(exc),
                llm_prompt_excerpt=self._last_prompt_excerpt,
            )
        self._state = next_state
        self._last_update_trace = trace
        return trace

    def _apply_strategy(self, observation: MarketObservation, fallback: AgentAction) -> AgentAction:
        state = self._state
        forecast_multiplier = (
            1.0
            + 0.18 * (state.demand_sensitivity - 0.5)
            + 0.03 * state.shock_responsiveness * observation.market_volatility
        )
        forecast = max(0, int(round(fallback.forecast_demand * forecast_multiplier)))

        price_gap = fallback.price - observation.market_avg_price
        price = (
            fallback.price
            + 0.55 * (state.price_aggressiveness - 0.5)
            - 0.35 * state.competitor_reactivity * price_gap
            + 0.10 * (state.risk_tolerance - state.inventory_caution)
        )
        price = round_to_step(price, self.config.price_step, self.config.price_floor, self.config.price_ceiling)

        shortage_pressure = max(0.0, observation.own_last_shortage) * (0.15 + state.risk_tolerance)
        inventory_drag = max(0.0, observation.own_inventory - fallback.quantity) * state.inventory_caution * 0.18
        quantity = (
            fallback.quantity
            + forecast * (0.18 * state.risk_tolerance - 0.14 * state.inventory_caution)
            + shortage_pressure
            - inventory_drag
        )
        quantity = int_round_to_step(quantity, self.config.quantity_step, 0, self.config.max_quantity)
        return AgentAction(forecast_demand=forecast, price=price, quantity=quantity)

    def _build_decision_trace(
        self,
        *,
        observation: MarketObservation,
        fallback: AgentAction,
        adjusted: AgentAction,
        reviewed: AgentAction,
    ) -> DecisionTrace:
        update_note = self._last_update_trace.reason if self._last_update_trace is not None else "initial strategy prior"
        risk_trace = getattr(self._risk_gate, "last_trace", {})
        risk_adjustment = str(risk_trace.get("adjustment", "none") or "none") if isinstance(risk_trace, dict) else "none"
        summary = (
            f"adaptive state {self._compact_state_text(self._state)}; "
            f"last update: {update_note}; "
            f"fallback forecast={fallback.forecast_demand}, price={fallback.price:.2f}, quantity={fallback.quantity}; "
            f"final forecast={reviewed.forecast_demand}, price={reviewed.price:.2f}, quantity={reviewed.quantity}"
        )
        del observation
        return DecisionTrace(
            source="llm-adaptive",
            summary=summary,
            forecast_base=float(fallback.forecast_demand),
            forecast_adjustment=float(adjusted.forecast_demand - fallback.forecast_demand),
            price_base=fallback.price,
            price_adjustment=adjusted.price - fallback.price,
            quantity_target=float(adjusted.quantity),
            risk_gate_adjustment=risk_adjustment,
            final_forecast=reviewed.forecast_demand,
            final_price=reviewed.price,
            final_quantity=reviewed.quantity,
            fallback_used=False,
            llm_status=self._last_update_trace.llm_status if self._last_update_trace is not None else "initial",
            llm_prompt_excerpt=self._last_update_trace.llm_prompt_excerpt if self._last_update_trace is not None else "",
        )

    def _query_strategy_delta(
        self,
        row: SettlementRow,
        round_rows: Sequence[SettlementRow],
    ) -> tuple[dict[str, float], str]:
        payload = self._prompt_payload(row, round_rows)
        system_prompt = (
            "You update a bounded strategy state for one agent in a repeated GPU spot market game.\n"
            f"Persistent personality: {self._personality.objective_bias}\n"
            f"Guidance: {self._personality.prompt_guidance}\n"
            "Return only valid JSON with numeric *_delta fields and a short reason. "
            "Each raw delta should be between -0.1 and 0.1."
        )
        user_prompt = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        self._last_prompt_excerpt = user_prompt[:500]
        plan = query_json_completion(
            client=self._client,
            llm_config=self._llm_config,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            retry_messages=[
                {
                    "role": "system",
                    "content": "Return one minified JSON object with the requested *_delta fields and reason.",
                },
                {"role": "user", "content": user_prompt},
            ],
        )
        return self._extract_delta(plan), str(plan.get("reason", "LLM adjusted bounded strategy parameters."))

    def _prompt_payload(self, row: SettlementRow, round_rows: Sequence[SettlementRow]) -> dict[str, Any]:
        competitors = [item for item in round_rows if item.agent_name != row.agent_name]
        competitor_avg_price = mean(item.price for item in competitors) if competitors else row.price
        best_profit = max(round_rows, key=lambda item: item.profit)
        return {
            "agent_name": row.agent_name,
            "agent_role": row.agent_role,
            "agent_persona": self.config.persona,
            "personality": self._personality.to_public_dict(),
            "current_strategy_state": self._state.to_public_dict(),
            "last_action": {
                "forecast_demand": row.forecast_demand,
                "price": row.price,
                "quantity": row.quantity,
            },
            "outcome": {
                "profit": row.profit,
                "cumulative_profit": row.cum_profit,
                "forecast_error_abs": row.forecast_error_abs,
                "inventory_end": row.inventory_end,
                "shortage": row.shortage_post_transfer,
                "service_rate": row.service_rate,
                "market_share": row.demand_share,
                "backlog_end": row.backlog_end,
                "late_units": row.late_units,
                "sla_queue_penalty": row.sla_queue_penalty,
                "price_pressure_cost": row.price_pressure_cost,
            },
            "market": {
                "round": row.round,
                "demand_true": row.demand_true,
                "demand_observed": row.demand_obs,
                "market_avg_price": row.market_avg_price,
                "competitor_avg_price": competitor_avg_price,
                "best_profit_agent": best_profit.agent_name,
                "best_profit": best_profit.profit,
                "shock_component": row.shock_component,
                "peer_reputations": [
                    {"agent_name": item.agent_name, "reputation": item.reputation_end}
                    for item in sorted(round_rows, key=lambda x: x.agent_name)
                ],
            },
            "instruction": (
                "Update strategy parameters for the next round. Keep personality persistent. "
                "Use small changes unless the outcome shows repeated shortage, backlog, or losses. "
                "Do not output direct price, quantity, or forecast."
            ),
        }

    def _extract_delta(self, payload: dict[str, Any]) -> dict[str, float]:
        delta: dict[str, float] = {}
        for field in StrategyState.fields():
            key = f"{field}_delta"
            try:
                delta[field] = float(payload.get(key, 0.0))
            except (TypeError, ValueError):
                delta[field] = 0.0
        return delta

    def _bound_delta(self, raw_delta: dict[str, float], state: StrategyState | None = None) -> dict[str, float]:
        bounded: dict[str, float] = {}
        for field in StrategyState.fields():
            raw_value = clamp(float(raw_delta.get(field, 0.0)), -0.1, 0.1)
            weighted = raw_value * float(self._personality.delta_weights.get(field, 1.0))
            limit = abs(float(self._personality.max_delta_by_param.get(field, 0.1)))
            if state is not None:
                current = float(getattr(state, field))
                room = (0.95 - current) if weighted > 0 else (current - 0.05)
                edge_damper = clamp(room / 0.25, 0.20, 1.0)
                weighted *= edge_damper
            bounded[field] = clamp(weighted, -limit, limit)
        return bounded

    def _fallback_delta(self, row: SettlementRow, round_rows: Sequence[SettlementRow]) -> dict[str, float]:
        del round_rows
        delta = {field: 0.0 for field in StrategyState.fields()}
        if row.shortage_post_transfer > 0:
            delta["risk_tolerance"] += 0.04
            delta["inventory_caution"] -= 0.03
            delta["demand_sensitivity"] += 0.03
        if row.inventory_end > max(20.0, row.quantity * 0.45):
            delta["inventory_caution"] += 0.05
            delta["price_aggressiveness"] -= 0.03
        if row.price > row.market_avg_price * 1.08 and row.service_rate < 0.9:
            delta["competitor_reactivity"] += 0.04
            delta["price_aggressiveness"] -= 0.04
        if abs(row.shock_component) >= 0.5 or row.forecast_error_abs > 35:
            delta["shock_responsiveness"] += 0.04
            delta["demand_sensitivity"] += 0.02
        if row.profit < 0:
            delta["risk_tolerance"] -= 0.02
            delta["inventory_caution"] += 0.02
        return delta

    def _fallback_reason(self, row: SettlementRow) -> str:
        if row.shortage_post_transfer > 0:
            return "Fallback update raised demand awareness after shortage pressure."
        if row.inventory_end > max(20.0, row.quantity * 0.45):
            return "Fallback update increased inventory caution after excess stock."
        if row.profit < 0:
            return "Fallback update reduced risk after a loss-making round."
        return "Fallback update kept strategy mostly stable after a balanced round."

    def _feedback_summary(self, row: SettlementRow, round_rows: Sequence[SettlementRow]) -> str:
        best_profit = max(round_rows, key=lambda item: item.profit)
        return (
            f"R{row.round} profit={row.profit:.2f}, service={row.service_rate:.0%}, "
            f"inventory={row.inventory_end:.1f}, shortage={row.shortage_post_transfer:.1f}, "
            f"best={best_profit.agent_name}:{best_profit.profit:.2f}"
        )

    def _compact_state_text(self, state: StrategyState) -> str:
        return (
            f"risk={state.risk_tolerance:.2f}, price={state.price_aggressiveness:.2f}, "
            f"demand={state.demand_sensitivity:.2f}, inventory={state.inventory_caution:.2f}, "
            f"shock={state.shock_responsiveness:.2f}, rivals={state.competitor_reactivity:.2f}"
        )
