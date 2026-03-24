from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import sys


def ensure_src_on_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))
    return repo_root


REPO_ROOT = ensure_src_on_path()

from pj_ag4.config import SimulationConfig, default_simulation_config  # noqa: E402
from pj_ag4.simulation import run_simulation  # noqa: E402

from quant.metrics import (  # noqa: E402
    AggregateBenchmark,
    AggregateMarketMetrics,
    AggregateSensitivityPoint,
    AgentAggregateMetrics,
    MarketRunMetrics,
    RunSummary,
    SensitivityPoint,
    aggregate_run_summaries,
    aggregate_sensitivity_points,
    summarize_csv_run,
)
from quant.strategies import ensure_quant_strategies_registered  # noqa: E402


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


def build_strategy_config(
    *,
    strategy_name: str,
    seed: int,
    rounds: int,
    output_dir: Path,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    llm_timeout_seconds: float = 30.0,
    market_overrides: dict[str, float] | None = None,
) -> SimulationConfig:
    ensure_quant_strategies_registered()
    config = build_simulation_config(
        seed=seed,
        rounds=rounds,
        output_dir=output_dir,
        agent_mode=strategy_name,
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )
    if market_overrides:
        config = replace(config, market=replace(config.market, **market_overrides))
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
    ensure_quant_strategies_registered()
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
    result = run_simulation(
        config,
        output_dir=output_dir,
        generate_figure=generate_figure,
        strategy_name=profile.kind,
    )
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
    ensure_quant_strategies_registered()
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
    ensure_quant_strategies_registered()
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
            result = run_simulation(
                config,
                output_dir=output_dir,
                generate_figure=plan.generate_figure,
                strategy_name=plan.strategy.kind,
            )
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


def summarize_benchmark_artifacts(artifacts: list[RunArtifact]) -> AggregateBenchmark:
    summaries = [artifact.summary for artifact in artifacts]
    return aggregate_run_summaries(summaries)


def summarize_sensitivity_artifacts(artifacts: list[RunArtifact]) -> list[AggregateSensitivityPoint]:
    points = [
        SensitivityPoint(
            strategy=artifact.strategy,
            seed=artifact.seed,
            parameter_name=artifact.parameter_name or "",
            parameter_value=artifact.parameter_value or 0.0,
            agent_metrics=artifact.summary.agents,
            market_metrics=artifact.summary.market,
        )
        for artifact in artifacts
    ]
    return aggregate_sensitivity_points(points)


def default_strategy_profiles(*, llm_enabled: bool = True) -> tuple[StrategyProfile, ...]:
    ensure_quant_strategies_registered()
    profiles = [
        StrategyProfile(name="heuristic", kind="heuristic"),
        StrategyProfile(name="rule_price_cutter", kind="rule_price_cutter"),
        StrategyProfile(name="rule_inventory_guard", kind="rule_inventory_guard"),
    ]
    if llm_enabled:
        profiles.append(StrategyProfile(name="llm", kind="llm"))
    return tuple(profiles)
