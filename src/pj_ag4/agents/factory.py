"""
重构2：
将策略名称（"heuristic"/"llm"）映射到具体的agent构建函数，
并通过strategy_registry分发。
"""

from typing import Any, Sequence

from ..config import AgentConfig, LLMConfig
from ..providers import build_openai_client
from ..strategy_registry import build_registered_agents, has_strategy, register_strategy
from .adaptive import AdaptiveLLMAgent
from .heuristic import HeuristicAgent, HyperscalerAgent, PremiumCloudAgent, SpotBrokerAgent
from .llm import LLMPolicyAgent


# 标记内置策略是否已注册
_BUILTINS_REGISTERED = False


def _build_heuristic_agent(cfg: AgentConfig) -> HeuristicAgent:
    """根据配置的role名称选择对应的heuristic agent子类。"""
    if cfg.role == "hyperscaler":
        return HyperscalerAgent(cfg)
    if cfg.role == "premium":
        return PremiumCloudAgent(cfg)
    if cfg.role == "spot":
        return SpotBrokerAgent(cfg)
    return HeuristicAgent(cfg)


def _build_heuristic_agents(
    configs: Sequence[AgentConfig],
    llm_config: LLMConfig | None = None,
) -> dict[str, HeuristicAgent]:
    """为所有配置创建heuristic agent字典。"""
    del llm_config
    return {cfg.name: _build_heuristic_agent(cfg) for cfg in configs}


def _build_llm_agents(
    configs: Sequence[AgentConfig],
    llm_config: LLMConfig | None = None,
) -> dict[str, Any]:
    """为所有配置创建LLM agent字典，每个agent内嵌一个heuristic fallback。"""
    if llm_config is None:
        raise ValueError("llm_config is required when mode='llm'")
    if not llm_config.api_key:
        raise ValueError("llm_config.api_key is required when mode='llm'")
    client = build_openai_client(llm_config)
    agents: dict[str, HeuristicAgent] = {}
    for cfg in configs:
        fallback_agent = _build_heuristic_agent(cfg)
        agents[cfg.name] = LLMPolicyAgent(
            cfg,
            llm_config=llm_config,
            fallback_agent=fallback_agent,
            client=client,
        )
    return agents


def _build_llm_adaptive_agents(
    configs: Sequence[AgentConfig],
    llm_config: LLMConfig | None = None,
) -> dict[str, Any]:
    """为所有配置创建LLM自适应策略agent，每个agent使用heuristic作为安全执行基线。"""
    if llm_config is None:
        raise ValueError("llm_config is required when mode='llm-adaptive'")
    if not llm_config.api_key:
        raise ValueError("llm_config.api_key is required when mode='llm-adaptive'")
    client = build_openai_client(llm_config)
    agents: dict[str, Any] = {}
    for cfg in configs:
        fallback_agent = _build_heuristic_agent(cfg)
        agents[cfg.name] = AdaptiveLLMAgent(
            cfg,
            llm_config=llm_config,
            fallback_agent=fallback_agent,
            client=client,
        )
    return agents


def ensure_builtin_strategies_registered() -> None:
    """
    确保 "heuristic" 和 "llm" 两个内置策略已注册到全局 registry。
    注册操作是幂等的——多次调用不会重复注册。
    """
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED and has_strategy("heuristic") and has_strategy("llm") and has_strategy("llm-adaptive"):
        return
    register_strategy("heuristic", title="Heuristic", builder=_build_heuristic_agents, replace=True)
    register_strategy("llm", title="LLM", builder=_build_llm_agents, replace=True)
    register_strategy("llm-adaptive", title="LLM Adaptive", builder=_build_llm_adaptive_agents, replace=True)
    _BUILTINS_REGISTERED = True


def build_agents(
    configs: Sequence[AgentConfig],
    *,
    mode: str = "heuristic",
    llm_config: LLMConfig | None = None,
) -> dict[str, Any]:
    """
    公共入口——构建指定模式下所有agent实例。
    参数:
      configs: AgentConfig列表（通常来自 SimulationConfig.agents）
      mode:   策略名称，默认 "heuristic"，可选 "llm"
      llm_config: LLM模式下的连接配置
    """
    ensure_builtin_strategies_registered()
    return build_registered_agents(mode, configs, llm_config=llm_config)
