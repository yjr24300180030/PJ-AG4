from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import math
import sys
from statistics import mean, pstdev
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from quant.common import RunArtifact, StrategyProfile, run_profile  # noqa: E402
from quant.reporting import write_dataclass_csv  # noqa: E402
from quant.strategies import DEFAULT_STRATEGIES, strategy_title  # noqa: E402


@dataclass(frozen=True)
class SensitivityGridRow:
    strategy: str
    seed: int
    beta_r: float
    sigma_obs: float
    total_profit: float
    fulfillment_ratio: float
    mean_sharpe_like: float
    mean_max_drawdown: float
    mean_avg_reputation: float
    mean_total_shortage: float


@dataclass(frozen=True)
class SensitivitySummaryRow:
    strategy: str
    beta_r: float
    sigma_obs: float
    runs: int
    mean_total_profit: float
    std_total_profit: float
    mean_fulfillment_ratio: float
    mean_sharpe_like: float
    mean_max_drawdown: float
    mean_avg_reputation: float
    mean_total_shortage: float


@dataclass(frozen=True)
class SensitivityResult:
    artifacts: list[RunArtifact]
    grid_rows: list[SensitivityGridRow]
    summary_rows: list[SensitivitySummaryRow]
    grid_csv: Path
    summary_csv: Path
    report_path: Path
    figure_path: Path


def _artifact_to_grid_row(artifact: RunArtifact, *, beta_r: float, sigma_obs: float) -> SensitivityGridRow:
    agent_metrics = artifact.summary.agent_metrics
    return SensitivityGridRow(
        strategy=artifact.strategy,
        seed=artifact.seed,
        beta_r=beta_r,
        sigma_obs=sigma_obs,
        total_profit=artifact.summary.market.total_profit,
        fulfillment_ratio=artifact.summary.market.fulfillment_ratio,
        mean_sharpe_like=mean(metric.sharpe_like for metric in agent_metrics) if agent_metrics else 0.0,
        mean_max_drawdown=mean(metric.max_drawdown for metric in agent_metrics) if agent_metrics else 0.0,
        mean_avg_reputation=mean(metric.avg_reputation for metric in agent_metrics) if agent_metrics else 0.0,
        mean_total_shortage=mean(metric.total_shortage for metric in agent_metrics) if agent_metrics else 0.0,
    )


def _aggregate_grid_rows(grid_rows: Sequence[SensitivityGridRow]) -> list[SensitivitySummaryRow]:
    grouped: dict[tuple[str, float, float], list[SensitivityGridRow]] = {}
    for row in grid_rows:
        grouped.setdefault((row.strategy, row.beta_r, row.sigma_obs), []).append(row)
    summary: list[SensitivitySummaryRow] = []
    for (strategy, beta_r, sigma_obs), rows in grouped.items():
        profits = [row.total_profit for row in rows]
        summary.append(
            SensitivitySummaryRow(
                strategy=strategy,
                beta_r=beta_r,
                sigma_obs=sigma_obs,
                runs=len(rows),
                mean_total_profit=mean(profits),
                std_total_profit=pstdev(profits) if len(profits) > 1 else 0.0,
                mean_fulfillment_ratio=mean(row.fulfillment_ratio for row in rows),
                mean_sharpe_like=mean(row.mean_sharpe_like for row in rows),
                mean_max_drawdown=mean(row.mean_max_drawdown for row in rows),
                mean_avg_reputation=mean(row.mean_avg_reputation for row in rows),
                mean_total_shortage=mean(row.mean_total_shortage for row in rows),
            )
        )
    return sorted(summary, key=lambda row: (row.strategy, row.beta_r, row.sigma_obs))


def _plot_heatmap(summary_rows: Sequence[SensitivitySummaryRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not summary_rows:
        return
    strategies = sorted({row.strategy for row in summary_rows})
    beta_values = sorted({row.beta_r for row in summary_rows})
    sigma_values = sorted({row.sigma_obs for row in summary_rows})
    fig, axes = plt.subplots(1, len(strategies), figsize=(5 * len(strategies), 4.5), squeeze=False)
    for axis, strategy in zip(axes[0], strategies, strict=True):
        lookup = {
            (row.strategy, row.beta_r, row.sigma_obs): row.mean_total_profit
            for row in summary_rows
        }
        matrix = [[math.nan for _ in beta_values] for _ in sigma_values]
        for y_index, sigma in enumerate(sigma_values):
            for x_index, beta in enumerate(beta_values):
                matrix[y_index][x_index] = lookup.get((strategy, beta, sigma), math.nan)
        image = axis.imshow(matrix, aspect="auto", origin="lower", cmap="viridis")
        axis.set_xticks(range(len(beta_values)))
        axis.set_xticklabels([f"{value:.2f}" for value in beta_values])
        axis.set_yticks(range(len(sigma_values)))
        axis.set_yticklabels([f"{value:.2f}" for value in sigma_values])
        axis.set_xlabel("beta_R")
        axis.set_ylabel("sigma_obs")
        axis.set_title(strategy_title(strategy))
        fig.colorbar(image, ax=axis, shrink=0.8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _write_report(path: Path, summary_rows: Sequence[SensitivitySummaryRow], figure_path: Path) -> None:
    lines: list[str] = []
    lines.append("# PJ-AG4 Sensitivity Report")
    lines.append("")
    lines.append(f"- Summary rows: {len(summary_rows)}")
    lines.append(f"- Figure: [{figure_path.name}]({figure_path.as_posix()})")
    lines.append("")
    lines.append("| Strategy | beta_R | sigma_obs | Mean Total Profit | Mean Fulfillment | Mean Sharpe-like | Mean Max Drawdown |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in summary_rows:
        lines.append(
            f"| {strategy_title(row.strategy)} | {row.beta_r:.3f} | {row.sigma_obs:.3f} | {row.mean_total_profit:.3f} | {row.mean_fulfillment_ratio:.3f} | {row.mean_sharpe_like:.3f} | {row.mean_max_drawdown:.3f} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_sensitivity_suite(
    *,
    strategies: Sequence[str] | None = None,
    seeds: Sequence[int] = (11, 23),
    rounds: int = 10,
    beta_r_values: Sequence[float] = (0.6, 1.2, 1.8),
    sigma_obs_values: Sequence[float] = (1.0, 5.0, 10.0),
    output_root: Path | str = Path("quant/outputs/sensitivity"),
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    timeout_seconds: float = 8.0,
) -> SensitivityResult:
    selected_strategies = tuple(strategies or ("heuristic",))
    output_root = Path(output_root)
    artifacts: list[RunArtifact] = []
    grid_rows: list[SensitivityGridRow] = []
    for strategy in selected_strategies:
        profile = StrategyProfile(name=strategy, kind=strategy)
        for beta_r in beta_r_values:
            for sigma_obs in sigma_obs_values:
                for seed in seeds:
                    artifact = run_profile(
                        profile,
                        seed=seed,
                        rounds=rounds,
                        output_root=output_root / "runs",
                        generate_figure=False,
                        llm_base_url=llm_base_url,
                        llm_api_key=llm_api_key,
                        llm_model=llm_model,
                        llm_timeout_seconds=timeout_seconds,
                        market_overrides={
                            "reputation_weight": beta_r,
                            "observation_noise_sigma": sigma_obs,
                        },
                    )
                    artifacts.append(artifact)
                    grid_rows.append(_artifact_to_grid_row(artifact, beta_r=beta_r, sigma_obs=sigma_obs))

    summary_rows = _aggregate_grid_rows(grid_rows)
    reports_dir = output_root / "reports"
    grid_csv = reports_dir / "sensitivity_grid.csv"
    summary_csv = reports_dir / "sensitivity_summary.csv"
    report_path = reports_dir / "sensitivity_report.md"
    figure_path = reports_dir / "sensitivity_heatmap.png"
    write_dataclass_csv(grid_csv, grid_rows)
    write_dataclass_csv(summary_csv, summary_rows)
    _plot_heatmap(summary_rows, figure_path)
    _write_report(report_path, summary_rows, figure_path)
    return SensitivityResult(
        artifacts=artifacts,
        grid_rows=grid_rows,
        summary_rows=summary_rows,
        grid_csv=grid_csv,
        summary_csv=summary_csv,
        report_path=report_path,
        figure_path=figure_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PJ-AG4 sensitivity analysis")
    parser.add_argument("--output-root", type=Path, default=Path("quant/outputs/sensitivity"))
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--seeds", type=int, nargs="+", default=[11, 23])
    parser.add_argument("--strategies", nargs="+", default=["heuristic"], choices=list(DEFAULT_STRATEGIES))
    parser.add_argument("--beta-r-values", type=float, nargs="+", default=[0.6, 1.2, 1.8])
    parser.add_argument("--sigma-obs-values", type=float, nargs="+", default=[1.0, 5.0, 10.0])
    parser.add_argument("--llm-base-url", type=str, default=None)
    parser.add_argument("--llm-api-key", type=str, default=None)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=8.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_sensitivity_suite(
        strategies=args.strategies,
        seeds=args.seeds,
        rounds=args.rounds,
        beta_r_values=args.beta_r_values,
        sigma_obs_values=args.sigma_obs_values,
        output_root=args.output_root,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
        timeout_seconds=args.timeout_seconds,
    )
    print(f"Grid CSV: {result.grid_csv}")
    print(f"Summary CSV: {result.summary_csv}")
    print(f"Report: {result.report_path}")
    print(f"Figure: {result.figure_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
