from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
import csv
import sys
from typing import Iterable, Sequence


def ensure_src_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return repo_root


REPO_ROOT = ensure_src_on_path()

from pj_ag4.agents import HeuristicAgent, build_agents as build_default_agents  # noqa: E402
from pj_ag4.config import AgentConfig, LLMConfig, SimulationConfig, default_simulation_config  # noqa: E402
import pj_ag4.simulation as simulation_module  # noqa: E402
from pj_ag4.simulation import run_simulation  # noqa: E402

from quant.metrics import (  # noqa: E402
    AggregateBenchmark,
    AggregateMarketMetrics,
    AggregateSensitivityPoint,
    AgentAggregateMetrics,
    MarketRunMetrics,
    RunSummary,
    SensitivityPoint,
    summarize_csv_run,
    aggregate_run_summaries,
    aggregate_sensitivity_points,
)


@dataclass(frozen=True)
class StrategyProfile:
    name: str
    kind: str


@dataclass(frozen=True)
class BenchmarkPlan:
    strategies: tuple[StrategyProfile, ...]
    seeds: tuple[int, ...]
    rounds: int = 10
    output_root: Path = REPO_ROOT / "quant" / "outputs" / "benchmarks"
    generate_figure: bool = False
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class SensitivityPlan:
    strategy: StrategyProfile
    seeds: tuple[int, ...]
    parameter: str
    values: tuple[float, ...]
    rounds: int = 10
    output_root: Path = REPO_ROOT / "quant" / "outputs" / "sensitivity"
    generate_figure: bool = False
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class RunArtifact:
    strategy: str
    kind: str
    seed: int
    rounds: int
    output_dir: Path
    csv_path: Path
    figure_path: Path | None
    summary: RunSummary
    parameter_name: str | None = None
    parameter_value: float | None = None


class TrendFollowerAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation, trend: float) -> float:
        return 0.55 * trend + 0.12 * observation.market_volatility

    def _price_adjustment(self, observation, forecast: int) -> float:
        demand_pressure = max(0.0, forecast - observation.own_inventory) / max(1.0, forecast)
        return -0.12 + 0.08 * demand_pressure - 0.06 * observation.market_volatility

    def _quantity_target(self, observation, forecast: int) -> float:
        return forecast * 0.88 + max(0.0, forecast - observation.own_inventory) * 0.30


class DefensiveAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation, trend: float) -> float:
        return 0.10 * trend

    def _price_adjustment(self, observation, forecast: int) -> float:
        return 0.85 + 0.45 * observation.own_reputation + 0.02 * observation.market_volatility

    def _quantity_target(self, observation, forecast: int) -> float:
        return forecast * 0.56 + max(0.0, 15.0 - observation.own_inventory) * 0.20


class AggressiveAgent(HeuristicAgent):
    def _forecast_adjustment(self, observation, trend: float) -> float:
        return 0.35 * trend + 0.08 * max(0.0, observation.own_last_shortage)

    def _price_adjustment(self, observation, forecast: int) -> float:
        reputation_discount = max(0.0, 0.60 - observation.own_reputation) * 0.18
        return -0.55 - 0.10 * observation.market_volatility - reputation_discount

    def _quantity_target(self, observation, forecast: int) -> float:
        return forecast * 1.05 + max(0.0, 25.0 - observation.own_inventory)


def _patched_build_agents(configs: Sequence[AgentConfig], *, mode: str = "heuristic", llm_config: LLMConfig | None = None):
    normalized = mode.lower()
    if normalized == "heuristic":
        return build_default_agents(configs, mode="heuristic", llm_config=llm_config)
    if normalized == "llm":
        if llm_config is None:
            raise ValueError("llm_config is required for llm mode")
        return build_default_agents(configs, mode="llm", llm_config=llm_config)
    if normalized == "trend":
        return {cfg.name: TrendFollowerAgent(cfg) for cfg in configs}
    if normalized == "defensive":
        return {cfg.name: DefensiveAgent(cfg) for cfg in configs}
    if normalized == "aggressive":
        return {cfg.name: AggressiveAgent(cfg) for cfg in configs}
    raise ValueError(f"unknown strategy mode: {mode}")


@contextmanager
def _patched_simulation_builder():
    original = simulation_module.build_agents
    simulation_module.build_agents = _patched_build_agents
    try:
        yield
    finally:
        simulation_module.build_agents = original


def build_simulation_config(
    *,
    seed: int,
    rounds: int,
    output_dir: Path,
    agent_mode: str,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: float = 30.0,
) -> SimulationConfig:
    config = default_simulation_config(
        seed=seed,
        rounds=rounds,
        output_dir=output_dir,
        agent_mode=agent_mode,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
    )
    if config.llm is not None and config.llm.timeout_seconds != llm_timeout_seconds:
        config = replace(config, llm=replace(config.llm, timeout_seconds=llm_timeout_seconds))
    return config


def run_profile(
    profile: StrategyProfile,
    *,
    seed: int,
    rounds: int,
    output_root: Path | None = None,
    generate_figure: bool = False,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: float = 30.0,
) -> RunArtifact:
    base_dir = Path(output_root or (REPO_ROOT / "quant" / "outputs"))
    output_dir = base_dir / profile.name / f"seed_{seed}"
    config = build_simulation_config(
        seed=seed,
        rounds=rounds,
        output_dir=output_dir,
        agent_mode=profile.kind,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )
    with _patched_simulation_builder():
        result = run_simulation(config, output_dir=output_dir, generate_figure=generate_figure)
    summary = summarize_csv_run(result.csv_path, strategy=profile.name, seed=seed)
    return RunArtifact(
        strategy=profile.name,
        kind=profile.kind,
        seed=seed,
        rounds=rounds,
        output_dir=output_dir,
        csv_path=result.csv_path,
        figure_path=result.figure_path,
        summary=summary,
    )


def run_benchmark_suite(plan: BenchmarkPlan) -> list[RunArtifact]:
    artifacts: list[RunArtifact] = []
    for profile in plan.strategies:
        for seed in plan.seeds:
            artifacts.append(
                run_profile(
                    profile,
                    seed=seed,
                    rounds=plan.rounds,
                    output_root=plan.output_root,
                    generate_figure=plan.generate_figure,
                    llm_base_url=plan.llm_base_url,
                    llm_api_key=plan.llm_api_key,
                    llm_model=plan.llm_model,
                    llm_timeout_seconds=plan.llm_timeout_seconds,
                )
            )
    return artifacts


def run_sensitivity_scan(plan: SensitivityPlan) -> list[RunArtifact]:
    artifacts: list[RunArtifact] = []
    for value in plan.values:
        for seed in plan.seeds:
            output_dir = Path(plan.output_root) / plan.strategy.name / f"{plan.parameter}_{value}" / f"seed_{seed}"
            config = build_simulation_config(
                seed=seed,
                rounds=plan.rounds,
                output_dir=output_dir,
                agent_mode=plan.strategy.kind,
                llm_base_url=plan.llm_base_url,
                llm_api_key=plan.llm_api_key,
                llm_model=plan.llm_model,
                llm_timeout_seconds=plan.llm_timeout_seconds,
            )
            if plan.parameter == "reputation_weight":
                config = replace(config, market=replace(config.market, reputation_weight=value))
            elif plan.parameter == "observation_noise_sigma":
                config = replace(config, market=replace(config.market, observation_noise_sigma=value))
            elif plan.parameter == "price_weight":
                config = replace(config, market=replace(config.market, price_weight=value))
            else:
                raise ValueError(f"unsupported sensitivity parameter: {plan.parameter}")
            with _patched_simulation_builder():
                result = run_simulation(config, output_dir=output_dir, generate_figure=plan.generate_figure)
            summary = summarize_csv_run(result.csv_path, strategy=plan.strategy.name, seed=seed)
            artifacts.append(
                RunArtifact(
                    strategy=plan.strategy.name,
                    kind=plan.strategy.kind,
                    seed=seed,
                    rounds=plan.rounds,
                    output_dir=output_dir,
                    csv_path=result.csv_path,
                    figure_path=result.figure_path,
                    summary=summary,
                    parameter_name=plan.parameter,
                    parameter_value=value,
                )
            )
    return artifacts


def sensitivity_points_from_runs(runs: Sequence[RunArtifact]) -> tuple[SensitivityPoint, ...]:
    points: list[SensitivityPoint] = []
    for run in runs:
        if run.parameter_name is None or run.parameter_value is None:
            continue
        agent_sharpe = (
            sum(metric.sharpe_like for metric in run.summary.agent_metrics) / len(run.summary.agent_metrics)
            if run.summary.agent_metrics
            else 0.0
        )
        agent_drawdown = (
            sum(metric.max_drawdown for metric in run.summary.agent_metrics) / len(run.summary.agent_metrics)
            if run.summary.agent_metrics
            else 0.0
        )
        points.append(
            SensitivityPoint(
                strategy=run.strategy,
                parameter=run.parameter_name,
                value=run.parameter_value,
                runs=1,
                mean_total_profit=run.summary.market.total_profit,
                std_total_profit=0.0,
                mean_fulfillment_ratio=run.summary.market.fulfillment_ratio,
                std_fulfillment_ratio=0.0,
                mean_sharpe_like=agent_sharpe,
                mean_max_drawdown=agent_drawdown,
            )
        )
    return tuple(points)


def default_strategy_profiles(llm_enabled: bool = False) -> tuple[StrategyProfile, ...]:
    profiles = [
        StrategyProfile(name="heuristic", kind="heuristic"),
        StrategyProfile(name="trend", kind="trend"),
        StrategyProfile(name="defensive", kind="defensive"),
        StrategyProfile(name="aggressive", kind="aggressive"),
    ]
    if llm_enabled:
        profiles.append(StrategyProfile(name="llm", kind="llm"))
    return tuple(profiles)
