"""
重构2：将 agent 的决策过程拆解为：
  styles:      风格定义与风格偏置函数（纯函数）
  risk:        风控审查（RiskGateStage）与份额计算
  pipeline:    管线编排基类（RolePipelineAgent）
  heuristic:   启发式 agent（规则驱动，无 LLM）
  llm:         LLM 驱动 agent + prompt 构建
  factory:     agent 工厂函数与策略注册
"""

from .heuristic import HeuristicAgent, HyperscalerAgent, PremiumCloudAgent, SpotBrokerAgent
from .llm import LLMContextPolicyAgent, LLMPolicyAgent
from .adaptive import AdaptiveLLMAgent
from .risk import RiskGateStage
from .factory import build_agents, ensure_builtin_strategies_registered

__all__ = [
    "HeuristicAgent",
    "HyperscalerAgent",
    "PremiumCloudAgent",
    "SpotBrokerAgent",
    "LLMContextPolicyAgent",
    "LLMPolicyAgent",
    "AdaptiveLLMAgent",
    "RiskGateStage",
    "build_agents",
    "ensure_builtin_strategies_registered",
]
