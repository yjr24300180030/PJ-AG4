"""
重构2：
依赖contracts
风格定义与风格偏置调整函数
"""

from ..contracts import MarketObservation

"""
下方字典用于 LLM prompt 拼接，向 LLM 解释每种风格的行为倾向。启发式模式下不使用。
"""

# 预测器风格：决定 agent 如何解读历史需求趋势
FORECASTER_STYLE_GUIDANCE = {
    "momentum_chaser": "Lean into trend continuation and respond quickly to rising demand pressure.",
    "signal_smoother": "Discount noisy spikes and prefer stable, reputation-aware demand estimates.",
    "volatility_reader": "React to short-term volatility and treat market swings as exploitable signals.",
}

# 定价器风格：决定 agent 的价格策略偏好
PRICER_STYLE_GUIDANCE = {
    "share_grabber": "Use aggressive pricing to capture flow and tolerate thinner margins.",
    "premium_keeper": "Protect price discipline and monetize reputation with a durable premium.",
    "spread_hunter": "Adjust prices tactically to capture transient spread and inventory opportunities.",
}

# 分配器风格：决定 agent 的产能/库存配置策略
ALLOCATOR_STYLE_GUIDANCE = {
    "capacity_expander": "Keep capacity ready and scale supply ahead of demand when possible.",
    "buffered_allocator": "Hold a moderate service buffer without overcommitting capital.",
    "inventory_light": "Stay light on inventory and favor flexibility over large buffers.",
}

# 风控风格：决定 RiskGateStage 的审查规则
RISK_STYLE_GUIDANCE = {
    "growth_tolerant": "Allow aggressive proposals unless they break hard market constraints.",
    "sla_guard": "Protect SLA reliability, price floor discipline, and brand reputation first.",
    "inventory_guard": "Avoid inventory bloat and tighten exposure when volatility is elevated.",
}

# 角色总览：每个角色的prompt开头
ROLE_GUIDANCE = {
    "hyperscaler": "You are the scale leader. Prioritize market share and continuity while avoiding catastrophic overstock.",
    "premium": "You are the premium cloud provider. Prioritize reputation, SLA stability, and disciplined pricing.",
    "spot": "You are the spot broker. Prioritize agility, short-term opportunities, and inventory flexibility.",
}


"""
以下三个函数在启发式模式下被 stage 调用，为数值添加风格偏置。
"""
def forecaster_style_adjustment(style: str, observation: MarketObservation, trend: float) -> float:
    """返回应加到需求预测上的风格偏置。"""
    if style == "momentum_chaser":
        # 追趋势：加大趋势权重，短缺时加量
        return 0.20 * trend + 0.06 * observation.market_volatility + 0.04 * max(0.0, observation.own_last_shortage)
    if style == "signal_smoother":
        # 信号平滑：用声誉抵消波动，压低噪声
        return -0.08 * trend + 0.05 * observation.own_reputation - 0.03 * observation.market_volatility
    if style == "volatility_reader":
        # 追逐不稳定：将波动视作机会
        return 0.12 * trend + 0.14 * observation.market_volatility
    return 0.0


def pricer_style_adjustment(style: str, observation: MarketObservation, forecast: int) -> float:
    """返回应加到基础价格上的风格偏置。"""
    inventory_pressure = max(0.0, observation.own_inventory - 15.0) / 100.0
    shortage_pressure = max(0.0, observation.own_last_shortage) / max(1.0, forecast)
    if style == "share_grabber":
        # 份额抢夺：主动降价，波动越大越激进，短缺时更甚
        return -0.22 - 0.05 * observation.market_volatility - 0.16 * shortage_pressure
    if style == "premium_keeper":
        # 溢价保护：使用声誉换溢价，在波动中求稳
        return 0.30 + 0.18 * observation.own_reputation + 0.03 * observation.market_volatility
    if style == "spread_hunter":
        # 价差猎手：库存低时抬价，在波动时积极
        return 0.04 - 0.16 * inventory_pressure + 0.05 * observation.market_volatility
    return 0.0


def allocator_style_adjustment(style: str, observation: MarketObservation, forecast: int) -> float:
    """返回应加到数量目标上的风格偏置。"""
    forecast_gap = max(0.0, forecast - observation.own_inventory)
    if style == "capacity_expander":
        # 容量扩张：预测缺口越大、库存越少，激进备货
        return 0.22 * forecast_gap + max(0.0, 10.0 - observation.own_inventory) * 0.5
    if style == "buffered_allocator":
        # 缓冲分配：保持适量缓冲，不过度备货
        return -0.10 * forecast + max(0.0, 18.0 - observation.own_inventory) * 0.4
    if style == "inventory_light":
        # 轻库存：压缩备货，波动中更灵活
        return -0.18 * forecast + 0.60 * observation.market_volatility
    return 0.0
