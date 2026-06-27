"""
重构2：
LLM驱动的Agent pipeline
  1. LLMPolicyAgent.decide() 先由 heuristic fallback计算以保证程序稳定性
  2. LLMPlanningStage拼接prompt调用LLM，返回JSON格式的决策计划
  3. 三个LLM stage从计划中提取各自字段
  4. RiskGateStage 做最终审查（与启发式模式共用）
  5. 异常时自动降级到 fallback action
"""

import json
from dataclasses import replace
from statistics import mean
from typing import Any, Sequence

from ..config import AgentConfig, LLMConfig
from ..contracts import AgentAction, DecisionTrace, MarketObservation, SettlementRow
from ..providers import build_openai_client, query_json_completion
from ..utils import int_round_to_step, round_to_step
from .pipeline import RolePipelineAgent
from .risk import RiskGateStage
from .styles import (
    ALLOCATOR_STYLE_GUIDANCE,
    FORECASTER_STYLE_GUIDANCE,
    PRICER_STYLE_GUIDANCE,
    RISK_STYLE_GUIDANCE,
    ROLE_GUIDANCE,
)


class LLMPlanningStage:
    """构建prompt、调用LLM、按观察值缓存结果。"""

    def __init__(self, config: AgentConfig, *, llm_config: LLMConfig, client: Any) -> None:
        self._config = config
        self._llm_config = llm_config
        self._client = client
        # 输入缓存：相同观察值跳过重复 LLM 调用
        self._cache_key: tuple[Any, ...] | None = None
        self._cache_value: dict[str, Any] | None = None
        self.last_prompt_excerpt = ""
        self.last_status = "idle"
        self.last_reasoning = ""

    def _cache_token(self, observation: MarketObservation) -> tuple[Any, ...]:
        """从观察中提取用于缓存的key字段。"""
        return (
            observation.round_index,
            observation.observed_demand,
            observation.own_inventory,
            observation.own_last_profit,
            observation.own_last_shortage,
            observation.own_reputation,
            observation.market_avg_price,
            observation.market_volatility,
        )

    def run(self, observation: MarketObservation, fallback: AgentAction) -> dict[str, Any]:
        """调用LLM返回JSON计划，命中缓存时直接返回。"""
        token = self._cache_token(observation)
        if self._cache_key == token and self._cache_value is not None:
            return self._cache_value
        system_prompt = self._system_prompt(compact=False)
        user_prompt = self._user_prompt(observation, fallback, compact=False)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        # 重试时用 compact prompt（减少 token、降低失败概率）
        retry_messages = [
            {"role": "system", "content": self._system_prompt(compact=True)},
            {"role": "user", "content": self._user_prompt(observation, fallback, compact=True)},
        ]
        self.last_prompt_excerpt = user_prompt[:500]
        self.last_status = "requested"
        plan = query_json_completion(
            client=self._client,
            llm_config=self._llm_config,
            messages=messages,
            retry_messages=retry_messages,
        )
        self.last_status = "ok"
        self.last_reasoning = str(plan.get("reasoning", plan.get("reason", "")))
        self._cache_key = token
        self._cache_value = plan
        return plan

    def _system_prompt(self, *, compact: bool) -> str:
        """构建system prompt，包含角色定义和风格指导。"""
        role_guidance = ROLE_GUIDANCE.get(self._config.role, "Act as a rational market participant.")
        stage_guidance = (
            f"Agent persona: {self._config.persona}\n"
            "Decision chain style:\n"
            f"- Forecaster: {FORECASTER_STYLE_GUIDANCE.get(self._config.forecaster_style, self._config.forecaster_style)}\n"
            f"- Pricer: {PRICER_STYLE_GUIDANCE.get(self._config.pricer_style, self._config.pricer_style)}\n"
            f"- Allocator: {ALLOCATOR_STYLE_GUIDANCE.get(self._config.allocator_style, self._config.allocator_style)}\n"
            f"- RiskGate: {RISK_STYLE_GUIDANCE.get(self._config.risk_style, self._config.risk_style)}\n"
        )
        prompt = (
            "You are a market simulation agent in a repeated GPU spot market game.\n"
            f"{role_guidance}\n{stage_guidance}"
            'Return only valid JSON with exactly these keys: '
            '"forecast_demand", "price", "quantity", "reasoning".\n'
            '"reasoning" should be a short sentence in Chinese explaining why you chose these values.\n'
            "Use numeric values for forecast_demand, price, and quantity. "
            "Do not add markdown or any text outside the JSON object."
        )
        if compact:
            prompt += "\nOutput one minified JSON object on a single line. Keep it under 40 tokens."
        return prompt

    def _user_prompt(self, observation: MarketObservation, fallback: AgentAction, *, compact: bool) -> str:
        """构建 user prompt，序列化观察数据与回退行为"""
        history_prices = [list(round_prices) for round_prices in observation.price_history[-5:]]
        history_reputation = [list(round_reputations) for round_reputations in observation.reputation_history[-5:]]
        payload = {
            "agent_name": self._config.name,
            "agent_role": self._config.role,
            "agent_persona": self._config.persona,
            "stage_styles": {
                "forecaster": self._config.forecaster_style,
                "pricer": self._config.pricer_style,
                "allocator": self._config.allocator_style,
                "risk_gate": self._config.risk_style,
            },
            "round_index": observation.round_index,
            "observed_demand": observation.observed_demand,
            "observed_demand_history": list(observation.observed_demand_history[-5:]),
            "price_history": history_prices,
            "reputation_history": history_reputation,
            "peer_reputations": list(observation.peer_reputations),
            "own_inventory": observation.own_inventory,
            "own_last_profit": observation.own_last_profit,
            "own_last_shortage": observation.own_last_shortage,
            "own_reputation": observation.own_reputation,
            "market_avg_price": observation.market_avg_price,
            "market_volatility": observation.market_volatility,
            "legal_price_range": {
                "min": self._config.price_floor,
                "max": self._config.price_ceiling,
                "step": self._config.price_step,
            },
            "legal_quantity_range": {
                "min": 0,
                "max": self._config.max_quantity,
                "step": self._config.quantity_step,
            },
            "fallback_action": {
                "forecast_demand": fallback.forecast_demand,
                "price": fallback.price,
                "quantity": fallback.quantity,
            },
            "instruction": (
                "Choose one-round-ahead demand forecast, price, and added quantity. "
                "Set quantity for your expected captured share of demand rather than the full market total. "
                "Stay within legal ranges. Favor valid JSON over verbosity."
            ),
        }
        if compact:
            # compact 版本只发送关键字段，减少 token 消耗
            payload = {
                "round_index": observation.round_index,
                "observed_demand": observation.observed_demand,
                "own_inventory": observation.own_inventory,
                "own_reputation": observation.own_reputation,
                "market_avg_price": observation.market_avg_price,
                "market_volatility": observation.market_volatility,
                "legal_price_range": payload["legal_price_range"],
                "legal_quantity_range": payload["legal_quantity_range"],
                "fallback_action": payload["fallback_action"],
                "instruction": "Return minified JSON only with forecast_demand, price, quantity, reasoning.",
            }
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


# 三个 stage 共享同一个 LLMPlanningStage 实例，
# 各自从返回的 dict 中提取不同字段。

class LLMForecasterStage:
    """从LLM计划中提取需求预测值。"""

    def __init__(self, planner: LLMPlanningStage) -> None:
        self._planner = planner
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, *, fallback: AgentAction | None = None) -> int:
        if fallback is None:
            raise ValueError("LLM 预测阶段需要 fallback action")
        plan = self._planner.run(observation, fallback)
        raw_value = float(plan.get("forecast_demand", fallback.forecast_demand))
        final_value = max(0, int(round(raw_value)))
        self.last_trace = {
            "base": fallback.forecast_demand,
            "adjustment": final_value - fallback.forecast_demand,
            "raw": raw_value,
            "final": float(final_value),
            "llm_status": self._planner.last_status,
            "llm_prompt_excerpt": self._planner.last_prompt_excerpt,
            "llm_reasoning": self._planner.last_reasoning,
        }
        return final_value


class LLMPricerStage:
    """从LLM计划中提取价格。"""

    def __init__(self, config: AgentConfig, planner: LLMPlanningStage) -> None:
        self._config = config
        self._planner = planner
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, forecast: int, *, fallback: AgentAction | None = None) -> float:
        del forecast
        if fallback is None:
            raise ValueError("LLM 定价阶段需要 fallback action")
        plan = self._planner.run(observation, fallback)
        raw_value = float(plan.get("price", fallback.price))
        final_value = round_to_step(
            raw_value,
            self._config.price_step,
            self._config.price_floor,
            self._config.price_ceiling,
        )
        self.last_trace = {
            "base": fallback.price,
            "adjustment": final_value - fallback.price,
            "raw": raw_value,
            "final": final_value,
            "llm_status": self._planner.last_status,
            "llm_prompt_excerpt": self._planner.last_prompt_excerpt,
            "llm_reasoning": self._planner.last_reasoning,
        }
        return final_value


class LLMAllocatorStage:
    """从LLM计划中提取数量。"""

    def __init__(self, config: AgentConfig, planner: LLMPlanningStage) -> None:
        self._config = config
        self._planner = planner
        self.last_trace: dict[str, float | str] = {}

    def run(self, observation: MarketObservation, forecast: int, price: float, *, fallback: AgentAction | None = None) -> int:
        del forecast, price
        if fallback is None:
            raise ValueError("LLM 分配阶段需要 fallback action")
        plan = self._planner.run(observation, fallback)
        raw_value = float(plan.get("quantity", fallback.quantity))
        final_value = int_round_to_step(
            raw_value,
            self._config.quantity_step,
            0,
            self._config.max_quantity,
        )
        self.last_trace = {
            "base": fallback.quantity,
            "adjustment": final_value - fallback.quantity,
            "target": raw_value,
            "final": float(final_value),
            "llm_status": self._planner.last_status,
            "llm_prompt_excerpt": self._planner.last_prompt_excerpt,
            "llm_reasoning": self._planner.last_reasoning,
        }
        return final_value


class LLMPolicyAgent(RolePipelineAgent):
    """使用LLM决策，异常时降级至heuristic fallback"""

    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        fallback_agent: RolePipelineAgent,
        client: Any,
    ) -> None:
        planner = LLMPlanningStage(config, llm_config=llm_config, client=client)
        super().__init__(
            config,
            forecaster=LLMForecasterStage(planner),
            pricer=LLMPricerStage(config, planner),
            allocator=LLMAllocatorStage(config, planner),
            risk_gate=RiskGateStage(config),
            trace_source="llm",
        )
        self._fallback_agent = fallback_agent

    def decide(self, observation: MarketObservation) -> AgentAction:
        """先用fallback计算兜底策略，再执行LLM pipeline，失败则降级。"""
        fallback = self._fallback_agent.decide(observation)
        try:
            return self._run_pipeline(observation, fallback=fallback)
        except Exception as exc:
            trace = DecisionTrace(
                source="llm_fallback",
                summary=(
                    f"LLM planning failed; fallback action used: "
                    f"forecast={fallback.forecast_demand}, price={fallback.price:.2f}, quantity={fallback.quantity}"
                ),
                final_forecast=fallback.forecast_demand,
                final_price=fallback.price,
                final_quantity=fallback.quantity,
                fallback_used=True,
                llm_status="fallback",
                llm_error=str(exc),
            )
            return replace(fallback, trace=trace)


class LLMContextPlanningStage(LLMPlanningStage):
    """LLM planner with a compressed rolling settlement context."""

    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        client: Any,
        max_context: int = 6,
    ) -> None:
        super().__init__(config, llm_config=llm_config, client=client)
        self._context_ring: list[dict[str, Any]] = []
        self._max_context = max(1, max_context)

    @property
    def context_size(self) -> int:
        return len(self._context_ring)

    def add_round_context(self, row: SettlementRow, round_rows: Sequence[SettlementRow]) -> None:
        """Compress one settlement row into the rolling context window."""
        competitors = [item for item in round_rows if item.agent_name != row.agent_name]
        competitor_avg_price = mean(item.price for item in competitors) if competitors else row.price
        best = max(round_rows, key=lambda item: item.profit)
        context = {
            "round": row.round,
            "signals": self._context_signals(row, competitor_avg_price=competitor_avg_price, best_agent=best.agent_name),
            "my": {
                "price": round(row.price, 2),
                "quantity": row.quantity,
                "forecast": row.forecast_demand,
                "profit": round(row.profit, 2),
                "cum_profit": round(row.cum_profit, 2),
                "service": round(row.service_rate, 3),
                "shortage": round(row.shortage_post_transfer, 2),
                "inventory": round(row.inventory_end, 2),
                "forecast_error": round(row.forecast_error_abs, 2),
                "share": round(row.demand_share, 3),
                "backlog": round(row.backlog_end, 2),
            },
            "market": {
                "avg_price": round(row.market_avg_price, 2),
                "competitor_avg_price": round(competitor_avg_price, 2),
                "true_demand": row.demand_true,
                "observed_demand": row.demand_obs,
                "total_sales": round(row.market_total_sales, 2),
                "shock": round(row.shock_component, 2),
            },
            "leader": {"agent": best.agent_name, "profit": round(best.profit, 2)},
        }
        self._context_ring.append(context)
        if len(self._context_ring) > self._max_context:
            self._context_ring.pop(0)
        self._cache_key = None
        self._cache_value = None

    def _context_signals(
        self,
        row: SettlementRow,
        *,
        competitor_avg_price: float,
        best_agent: str,
    ) -> list[str]:
        signals: list[str] = []
        if row.shortage_post_transfer > 0 or row.backlog_end > 0:
            signals.append("service_pressure")
        if row.inventory_end > max(20.0, row.quantity * 0.45):
            signals.append("inventory_pressure")
        if row.profit < 0:
            signals.append("loss_round")
        if row.forecast_error_abs > 35 or abs(row.shock_component) >= 0.5:
            signals.append("forecast_or_shock_error")
        if row.price > competitor_avg_price * 1.08:
            signals.append("priced_above_competitors")
        if row.price < competitor_avg_price * 0.92:
            signals.append("priced_below_competitors")
        if row.agent_name != best_agent:
            signals.append("not_profit_leader")
        return signals or ["stable"]

    def _history_signals(self) -> list[str]:
        signals: list[str] = []
        for item in self._context_ring:
            for signal in item.get("signals", []):
                if signal not in signals:
                    signals.append(signal)
        return signals

    def _rolling_context_payload(self, *, compact: bool) -> dict[str, Any]:
        if not self._context_ring:
            return {
                "window": self._max_context,
                "selection": "none_until_first_settlement",
                "compression": "empty",
                "history": [],
            }
        if compact:
            history = [
                {
                    "round": item["round"],
                    "signals": item["signals"],
                    "profit": item["my"]["profit"],
                    "service": item["my"]["service"],
                    "inventory": item["my"]["inventory"],
                    "leader": item["leader"]["agent"],
                }
                for item in self._context_ring
            ]
            compression = "signal_profit_service_inventory_summary"
        else:
            history = list(self._context_ring)
            compression = "settlement_rows_compressed_to_action_outcome_market_leader"
        return {
            "window": self._max_context,
            "selection": "latest_settlement_summaries",
            "compression": compression,
            "active_signals": self._history_signals(),
            "history": history,
        }

    def _user_prompt(self, observation: MarketObservation, fallback: AgentAction, *, compact: bool) -> str:
        base_prompt = super()._user_prompt(observation, fallback, compact=compact)
        payload = json.loads(base_prompt)
        payload["llm_context"] = self._rolling_context_payload(compact=compact)
        payload["instruction"] = (
            f"{payload['instruction']} Use llm_context as compressed historical evidence; "
            "the current observation remains the freshest signal."
        )
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


class LLMContextPolicyAgent(LLMPolicyAgent):
    """LLM policy agent with settlement history context management."""

    def __init__(
        self,
        config: AgentConfig,
        *,
        llm_config: LLMConfig,
        fallback_agent: RolePipelineAgent,
        client: Any,
        max_context: int = 6,
    ) -> None:
        planner = LLMContextPlanningStage(
            config,
            llm_config=llm_config,
            client=client,
            max_context=max_context,
        )
        RolePipelineAgent.__init__(
            self,
            config,
            forecaster=LLMForecasterStage(planner),
            pricer=LLMPricerStage(config, planner),
            allocator=LLMAllocatorStage(config, planner),
            risk_gate=RiskGateStage(config),
            trace_source="llm-context",
        )
        self._fallback_agent = fallback_agent
        self._planner = planner

    def observe_result(self, row: SettlementRow, round_rows: Sequence[SettlementRow]) -> None:
        self._planner.add_round_context(row, round_rows)
