from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import sys
from typing import Sequence


def _ensure_repo_root_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    src_root_str = str(repo_root / "src")
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)


_ensure_repo_root_on_path()

from quant.run_benchmarks import run_benchmark_suite  # noqa: E402
from quant.run_sensitivity import run_sensitivity_suite  # noqa: E402
from quant.strategies import DEFAULT_STRATEGIES, strategy_title  # noqa: E402


@dataclass(frozen=True)
class FullQuantResult:
    benchmark_report: Path
    benchmark_figure: Path
    sensitivity_report: Path
    sensitivity_figure: Path
    full_report: Path


def _write_full_report(
    *,
    output_path: Path,
    benchmark_report: Path,
    benchmark_figure: Path,
    benchmark_strategy_lines: Sequence[str],
    sensitivity_report: Path,
    sensitivity_figure: Path,
    sensitivity_lines: Sequence[str],
) -> None:
    lines: list[str] = []
    lines.append("# PJ-AG4 Full Quant Report")
    lines.append("")
    lines.append("## Benchmark")
    lines.append("")
    lines.append(f"- Report: [{benchmark_report.name}]({benchmark_report.as_posix()})")
    lines.append(f"- Figure: [{benchmark_figure.name}]({benchmark_figure.as_posix()})")
    lines.extend(benchmark_strategy_lines)
    lines.append("")
    lines.append("## Sensitivity")
    lines.append("")
    lines.append(f"- Report: [{sensitivity_report.name}]({sensitivity_report.as_posix()})")
    lines.append(f"- Figure: [{sensitivity_figure.name}]({sensitivity_figure.as_posix()})")
    lines.extend(sensitivity_lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _benchmark_lines(strategy_metrics) -> list[str]:
    if not strategy_metrics:
        return ["- No benchmark rows found."]
    ordered = sorted(strategy_metrics, key=lambda row: row.mean_final_cum_profit, reverse=True)
    lines = ["", "### Benchmark Ranking", ""]
    for index, row in enumerate(ordered, start=1):
        lines.append(
            f"- {index}. {strategy_title(row.strategy)}: mean final cumulative profit {row.mean_final_cum_profit:.3f}, mean default rate {row.mean_default_rate:.3f}"
        )
    return lines


def _sensitivity_lines(summary_rows) -> list[str]:
    if not summary_rows:
        return ["- No sensitivity rows found."]
    ordered = sorted(summary_rows, key=lambda row: row.mean_final_cum_profit, reverse=True)
    best = ordered[0]
    return [
        "",
        "### Sensitivity Best Point",
        "",
        f"- Best observed combination: {strategy_title(best.strategy)} with beta_R={best.beta_r:.3f}, sigma_obs={best.sigma_obs:.3f}",
        f"- Mean final cumulative profit: {best.mean_final_cum_profit:.3f}",
        f"- Mean default rate: {best.mean_default_rate:.3f}",
    ]


def run_full_quant(
    *,
    output_root: Path | str = Path("quant/outputs/full_quant"),
    benchmark_rounds: int = 10,
    benchmark_seeds: Sequence[int] = (7, 11),
    benchmark_strategies: Sequence[str] | None = None,
    sensitivity_rounds: int = 10,
    sensitivity_seeds: Sequence[int] = (11, 23),
    sensitivity_strategies: Sequence[str] | None = None,
    beta_r_values: Sequence[float] = (0.6, 1.2, 1.8),
    sigma_obs_values: Sequence[float] = (1.0, 5.0, 10.0),
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    timeout_seconds: float = 8.0,
) -> FullQuantResult:
    output_root = Path(output_root)
    benchmark_result = run_benchmark_suite(
        strategies=benchmark_strategies or DEFAULT_STRATEGIES,
        seeds=benchmark_seeds,
        rounds=benchmark_rounds,
        output_root=output_root / "benchmarks",
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        timeout_seconds=timeout_seconds,
        generate_run_figures=False,
    )
    sensitivity_result = run_sensitivity_suite(
        strategies=sensitivity_strategies or ("heuristic",),
        seeds=sensitivity_seeds,
        rounds=sensitivity_rounds,
        beta_r_values=beta_r_values,
        sigma_obs_values=sigma_obs_values,
        output_root=output_root / "sensitivity",
        llm_base_url=llm_base_url,
        llm_api_key=llm_api_key,
        llm_model=llm_model,
        timeout_seconds=timeout_seconds,
    )
    full_report = output_root / "full_quant_report.md"
    _write_full_report(
        output_path=full_report,
        benchmark_report=benchmark_result.report_path,
        benchmark_figure=benchmark_result.figure_path,
        benchmark_strategy_lines=_benchmark_lines(benchmark_result.strategy_metrics),
        sensitivity_report=sensitivity_result.report_path,
        sensitivity_figure=sensitivity_result.figure_path,
        sensitivity_lines=_sensitivity_lines(sensitivity_result.summary_rows),
    )
    return FullQuantResult(
        benchmark_report=benchmark_result.report_path,
        benchmark_figure=benchmark_result.figure_path,
        sensitivity_report=sensitivity_result.report_path,
        sensitivity_figure=sensitivity_result.figure_path,
        full_report=full_report,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the full PJ-AG4 quant workflow")
    parser.add_argument("--output-root", type=Path, default=Path("quant/outputs/full_quant"))
    parser.add_argument("--benchmark-rounds", type=int, default=10)
    parser.add_argument("--benchmark-seeds", type=int, nargs="+", default=[7, 11])
    parser.add_argument("--benchmark-strategies", nargs="+", default=list(DEFAULT_STRATEGIES), choices=list(DEFAULT_STRATEGIES))
    parser.add_argument("--sensitivity-rounds", type=int, default=10)
    parser.add_argument("--sensitivity-seeds", type=int, nargs="+", default=[11, 23])
    parser.add_argument("--sensitivity-strategies", nargs="+", default=["heuristic"], choices=list(DEFAULT_STRATEGIES))
    parser.add_argument("--beta-r-values", type=float, nargs="+", default=[0.6, 1.2, 1.8])
    parser.add_argument("--sigma-obs-values", type=float, nargs="+", default=[1.0, 5.0, 10.0])
    parser.add_argument("--llm-base-url", type=str, default=None)
    parser.add_argument("--llm-api-key", type=str, default=None)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_full_quant(
        output_root=args.output_root,
        benchmark_rounds=args.benchmark_rounds,
        benchmark_seeds=args.benchmark_seeds,
        benchmark_strategies=args.benchmark_strategies,
        sensitivity_rounds=args.sensitivity_rounds,
        sensitivity_seeds=args.sensitivity_seeds,
        sensitivity_strategies=args.sensitivity_strategies,
        beta_r_values=args.beta_r_values,
        sigma_obs_values=args.sigma_obs_values,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
        timeout_seconds=args.timeout_seconds,
    )
    print(f"Benchmark report: {result.benchmark_report}")
    print(f"Benchmark figure: {result.benchmark_figure}")
    print(f"Sensitivity report: {result.sensitivity_report}")
    print(f"Sensitivity figure: {result.sensitivity_figure}")
    print(f"Full report: {result.full_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
