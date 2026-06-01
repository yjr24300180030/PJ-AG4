"""
重构2：
依赖config和contract以及utils模块
风控审查，对前三级（预测→定价→分配）产出的初步行为做最终约束，
包括风险风格调整、库存目标校验、低声誉兜底
"""

from ..config import AgentConfig
from ..contracts import AgentAction, MarketObservation
from ..utils import clamp, int_round_to_step, round_to_step


def expected_capture_share(
    config: AgentConfig,
    observation: MarketObservation,
    planned_price: float,
) -> float:
    """
    估算该 agent 在当前价格和声誉下获得的需求比例
    公式：
      base_share = 1/N（平等起点）
      + reputation_edge（声誉优势，幅度 0.45）
      + price_edge（价格越低于均价，份额越高，幅度 -0.18）
      + style_bias（share_grabber +0.06，premium_keeper -0.04）
    结果被固定至[0.12, 0.72]
    """
    # 排除自身后的同行声誉列表
    peer_reputations = [value for _, value in observation.peer_reputations if _ != config.name]
    agent_count = max(1, len(peer_reputations) + 1)
    base_share = 1.0 / agent_count
    avg_peer_reputation = (
        sum(peer_reputations) / len(peer_reputations) if peer_reputations else observation.own_reputation
    )
    reputation_edge = 0.45 * (observation.own_reputation - avg_peer_reputation)
    price_edge = -0.18 * (planned_price - observation.market_avg_price)
    style_bias = 0.0
    if config.pricer_style == "share_grabber":
        style_bias += 0.06
    elif config.pricer_style == "premium_keeper":
        style_bias -= 0.04
    return clamp(base_share + reputation_edge + price_edge + style_bias, 0.12, 0.72)


def inventory_target_total(
    config: AgentConfig,
    observation: MarketObservation,
    forecast: int,
    planned_price: float,
) -> float:
    """
    计算 agent 应持有的理想库存总量
    考虑预期捕获需求 + 短缺缓冲，并按risk_style做系数缩放。
    """
    share = expected_capture_share(config, observation, planned_price)
    expected_captured_demand = forecast * share
    shortage_buffer = min(observation.own_last_shortage, max(6.0, forecast * 0.12))
    if config.risk_style == "growth_tolerant":
        # 激进派：多备 18%，额外加 10 单位缓冲
        return max(18.0, expected_captured_demand * 1.18 + 10.0 + shortage_buffer)
    if config.risk_style == "sla_guard":
        # 保SLA：多备 10%，缓冲打 8 折
        return max(16.0, expected_captured_demand * 1.10 + 8.0 + 0.8 * shortage_buffer)
    if config.risk_style == "inventory_guard":
        # 控库存：反而压缩到 92%，减少资金占用
        return max(12.0, expected_captured_demand * 0.92 + 5.0 + 0.5 * shortage_buffer)
    return max(15.0, expected_captured_demand + 6.0 + 0.6 * shortage_buffer)


class RiskGateStage:
    """
    最终风险审查——按风险风格产出最终的AgentAction。
    """

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self.last_trace: dict[str, object] = {}

    def review(
        self,
        observation: MarketObservation,
        draft: AgentAction,
        *,
        fallback: AgentAction | None = None,
    ) -> AgentAction:
        """审查初步结果，基于风险风格做调整，然后约束到合法范围。"""
        reviewed_price = draft.price
        reviewed_quantity = float(draft.quantity)
        reviewed_forecast = draft.forecast_demand
        style = self._config.risk_style
        adjustments: list[str] = []

        # ── 按风格做风格化调整 ──
        if style == "growth_tolerant":
            # 增长容忍：上轮短缺则追加一个 step 的产能
            if observation.own_last_shortage > 0:
                reviewed_quantity += self._config.quantity_step
                adjustments.append("growth_tolerant added capacity after shortage")
        elif style == "sla_guard":
            # SLA 守护：价格不低于均价，声誉或短缺有问题时压缩量
            if reviewed_price < observation.market_avg_price:
                adjustments.append("sla_guard lifted price to market average")
                reviewed_price = observation.market_avg_price
            if observation.own_last_shortage > 0 or observation.own_reputation < 0.85:
                adjustments.append("sla_guard reduced quantity under SLA/reputation pressure")
                reviewed_quantity = min(reviewed_quantity, max(0.0, reviewed_forecast * 0.80))
        elif style == "inventory_guard":
            # 库存守护：量不超过目标减去已有库存，高波动时提价
            target_total = max(reviewed_forecast * 0.75 + 12.0, 20.0)
            capped_quantity = min(reviewed_quantity, max(0.0, target_total - observation.own_inventory))
            if capped_quantity < reviewed_quantity:
                adjustments.append("inventory_guard capped quantity to target inventory")
            reviewed_quantity = capped_quantity
            if observation.market_volatility > 5.0:
                if reviewed_price < observation.market_avg_price:
                    adjustments.append("inventory_guard lifted price under volatility")
                    reviewed_price = observation.market_avg_price

        # ── 通用约束：量不超过库存目标 ──
        inv_target = inventory_target_total(self._config, observation, reviewed_forecast, reviewed_price)
        capped_quantity = min(reviewed_quantity, max(0.0, inv_target - observation.own_inventory))
        if capped_quantity < reviewed_quantity:
            adjustments.append("inventory target capped quantity")
        reviewed_quantity = capped_quantity

        # ── 低声誉兜底：价格不低于 fallback ──
        if fallback is not None and observation.own_reputation < 0.35:
            if reviewed_price < fallback.price:
                adjustments.append("low reputation fallback lifted price")
                reviewed_price = fallback.price

        final_action = AgentAction(
            forecast_demand=max(0, int(round(reviewed_forecast))),
            price=round_to_step(
                reviewed_price, self._config.price_step, self._config.price_floor, self._config.price_ceiling
            ),
            quantity=int_round_to_step(
                reviewed_quantity, self._config.quantity_step, 0, self._config.max_quantity
            ),
        )
        self.last_trace = {
            "draft_price": draft.price,
            "draft_quantity": draft.quantity,
            "final_price": final_action.price,
            "final_quantity": final_action.quantity,
            "adjustment": "; ".join(adjustments) if adjustments else "none",
        }
        return final_action
