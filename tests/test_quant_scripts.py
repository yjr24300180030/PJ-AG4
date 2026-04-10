from __future__ import annotations

from pathlib import Path

from quant.run_benchmarks import run_benchmark_suite
from quant.run_full_quant import run_full_quant
from quant.run_sensitivity import run_sensitivity_suite


def test_run_benchmark_suite_writes_expected_artifacts(tmp_path: Path) -> None:
    result = run_benchmark_suite(
        strategies=("heuristic",),
        seeds=(7,),
        rounds=2,
        output_root=tmp_path / "benchmarks",
    )

    assert result.run_agent_metrics_csv.exists()
    assert result.run_market_metrics_csv.exists()
    assert result.aggregate_csv.exists()
    assert result.report_path.exists()
    assert result.figure_path.exists()
    assert len(result.aggregates) == 1


def test_run_sensitivity_suite_writes_expected_artifacts(tmp_path: Path) -> None:
    result = run_sensitivity_suite(
        strategies=("heuristic",),
        seeds=(7,),
        rounds=2,
        beta_r_values=(1.2,),
        sigma_obs_values=(5.0,),
        output_root=tmp_path / "sensitivity",
    )

    assert result.grid_csv.exists()
    assert result.summary_csv.exists()
    assert result.report_path.exists()
    assert result.figure_path.exists()
    assert len(result.summary_rows) == 1


def test_run_full_quant_writes_full_report(tmp_path: Path) -> None:
    result = run_full_quant(
        output_root=tmp_path / "full_quant",
        benchmark_rounds=2,
        benchmark_seeds=(7,),
        benchmark_strategies=("heuristic",),
        sensitivity_rounds=2,
        sensitivity_seeds=(7,),
        sensitivity_strategies=("heuristic",),
        beta_r_values=(1.2,),
        sigma_obs_values=(5.0,),
    )

    assert result.benchmark_report.exists()
    assert result.sensitivity_report.exists()
    assert result.full_report.exists()
