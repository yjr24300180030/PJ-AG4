from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .config import AgentConfig, LLMConfig


StrategyBuilder = Callable[[Sequence[AgentConfig], LLMConfig | None], dict[str, Any]]


@dataclass(frozen=True)
class StrategyRegistration:
    name: str
    title: str
    builder: StrategyBuilder


_REGISTRY: dict[str, StrategyRegistration] = {}


def register_strategy(
    name: str,
    *,
    title: str,
    builder: StrategyBuilder,
    replace: bool = False,
) -> None:
    normalized = name.lower()
    if normalized in _REGISTRY and not replace:
        raise ValueError(f"strategy already registered: {name}")
    _REGISTRY[normalized] = StrategyRegistration(name=normalized, title=title, builder=builder)


def has_strategy(name: str) -> bool:
    return name.lower() in _REGISTRY


def build_registered_agents(
    name: str,
    configs: Sequence[AgentConfig],
    *,
    llm_config: LLMConfig | None = None,
) -> dict[str, Any]:
    normalized = name.lower()
    if normalized not in _REGISTRY:
        raise ValueError(f"unknown strategy: {name}")
    return _REGISTRY[normalized].builder(configs, llm_config)


def strategy_title(name: str) -> str:
    normalized = name.lower()
    if normalized not in _REGISTRY:
        return name
    return _REGISTRY[normalized].title


def registered_strategies() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
