from __future__ import annotations

from pathlib import Path

from quant.common import (
    BenchmarkPlan,
    SensitivityPlan,
    StrategyProfile,
    run_benchmark_suite,
    run_sensitivity_scan,
    sensitivity_points_from_runs,
    summarize_benchmark_artifacts,
    summarize_sensitivity_artifacts,
)


def test_summarize_benchmark_artifacts_returns_aggregate_tuple(tmp_path: Path) -> None:
    plan = BenchmarkPlan(
        strategies=(StrategyProfile(name="heuristic", kind="heuristic"),),
        seeds=(7,),
        rounds=2,
        output_root=tmp_path / "bench",
    )

    artifacts = run_benchmark_suite(plan)
    summary = summarize_benchmark_artifacts(artifacts)

    assert len(summary) == 1
    assert summary[0].strategy == "heuristic"


def test_summarize_sensitivity_artifacts_uses_current_runsummary_shape(tmp_path: Path) -> None:
    plan = SensitivityPlan(
        strategy=StrategyProfile(name="heuristic", kind="heuristic"),
        seeds=(7,),
        parameter="reputation_weight",
        values=(1.2,),
        rounds=2,
        output_root=tmp_path / "sensitivity",
    )

    artifacts = run_sensitivity_scan(plan)
    points = sensitivity_points_from_runs(artifacts)
    summary = summarize_sensitivity_artifacts(artifacts)

    assert len(points) == 1
    assert points[0].parameter == "reputation_weight"
    assert len(summary) == 1
    assert summary[0].parameter == "reputation_weight"
