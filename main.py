"""Reproduce the final PJ-AG4 experiment matrix."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pj_ag4.config import load_runtime_env  # noqa: E402
from quant.common import RunArtifact, StrategyProfile, run_profile  # noqa: E402


SCENARIOS = ("baseline", "price_war", "supply_shock", "high_volatility", "no_reputation", "no_transfer")
AGENT_MODES = ("heuristic", "llm", "llm-context", "llm-adaptive", "llm-context-adaptive")
LLM_AGENT_MODES = ("llm", "llm-context", "llm-adaptive", "llm-context-adaptive")


@dataclass(frozen=True)
class MatrixSummary:
    scenario: str
    agent_mode: str
    seed: int
    rounds: int
    total_profit: float
    fulfillment_ratio: float
    avg_price: float
    total_shortage: float
    default_events: int
    dump_events: int
    csv_path: str


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _validate_choices(values: Sequence[str], *, allowed: Sequence[str], label: str) -> tuple[str, ...]:
    unknown = sorted(set(values) - set(allowed))
    if unknown:
        raise ValueError(f"unknown {label}: {', '.join(unknown)}")
    return tuple(values)


def _requires_llm(agent_modes: Sequence[str]) -> bool:
    return any(mode in LLM_AGENT_MODES for mode in agent_modes)


def _resolve_llm_config(
    *,
    agent_modes: Sequence[str],
    llm_base_url: str | None,
    llm_api_key: str | None,
    llm_model: str | None,
) -> tuple[str | None, str | None, str | None]:
    load_runtime_env()
    resolved_api_key = (
        llm_api_key
        or os.getenv("PJ_AG4_LLM_API_KEY")
        or os.getenv("PJ_AG4_OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    resolved_base_url = (
        llm_base_url
        or os.getenv("PJ_AG4_LLM_BASE_URL")
        or os.getenv("PJ_AG4_OPENAI_BASE_URL")
    )
    resolved_model = (
        llm_model
        or os.getenv("PJ_AG4_LLM_MODEL")
        or os.getenv("PJ_AG4_OPENAI_MODEL")
        or "gemini-3-flash"
    )
    if _requires_llm(agent_modes):
        missing = []
        if not resolved_api_key:
            missing.append("PJ_AG4_LLM_API_KEY or --llm-api-key")
        if not resolved_base_url:
            missing.append("PJ_AG4_LLM_BASE_URL or --llm-base-url")
        if missing:
            raise RuntimeError(
                "LLM experiment matrix requires "
                + " and ".join(missing)
                + ". Set them in the shell or in .env before running python main.py."
            )
    return resolved_base_url, resolved_api_key, resolved_model


def _artifact_to_summary(artifact: RunArtifact) -> MatrixSummary:
    market = artifact.summary.market
    agent_metrics = artifact.summary.agent_metrics
    return MatrixSummary(
        scenario=artifact.scenario,
        agent_mode=artifact.strategy,
        seed=artifact.seed,
        rounds=artifact.rounds,
        total_profit=market.total_profit,
        fulfillment_ratio=market.fulfillment_ratio,
        avg_price=market.avg_price,
        total_shortage=sum(item.total_shortage for item in agent_metrics),
        default_events=sum(item.default_events for item in agent_metrics),
        dump_events=sum(item.dump_events for item in agent_metrics),
        csv_path=str(artifact.csv_path),
    )


def _write_summary(path: Path, rows: Sequence[MatrixSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(MatrixSummary.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: getattr(row, field) for field in fieldnames})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reproduce the PJ-AG4 final experiment matrix")
    parser.add_argument("--rounds", type=int, default=12, help="Rounds per run")
    parser.add_argument("--seed", type=int, default=7, help="Random seed")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("outputs/reproduce"),
        help="Directory for reproduced matrix outputs",
    )
    parser.add_argument(
        "--scenarios",
        type=_split_csv,
        default=SCENARIOS,
        help="Comma-separated scenarios to run",
    )
    parser.add_argument(
        "--agent-modes",
        type=_split_csv,
        default=AGENT_MODES,
        help="Comma-separated agent modes to run",
    )
    parser.add_argument("--llm-base-url", type=str, default=None)
    parser.add_argument("--llm-api-key", type=str, default=None)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--figures", action="store_true", help="Generate per-run figures")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scenarios = _validate_choices(args.scenarios, allowed=SCENARIOS, label="scenario")
    agent_modes = _validate_choices(args.agent_modes, allowed=AGENT_MODES, label="agent mode")
    llm_base_url, llm_api_key, llm_model = _resolve_llm_config(
        agent_modes=agent_modes,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
    )

    artifacts: list[RunArtifact] = []
    for agent_mode in agent_modes:
        profile = StrategyProfile(name=agent_mode, kind=agent_mode)
        for scenario in scenarios:
            print(f"Running {agent_mode} / {scenario} / seed {args.seed}")
            artifacts.append(
                run_profile(
                    profile,
                    seed=args.seed,
                    rounds=args.rounds,
                    output_root=args.output_root / "runs",
                    generate_figure=args.figures,
                    generate_report=False,
                    llm_base_url=llm_base_url,
                    llm_api_key=llm_api_key,
                    llm_model=llm_model,
                    llm_timeout_seconds=args.timeout_seconds,
                    scenario=scenario,
                )
            )

    summary_path = args.output_root / "simulation_result.csv"
    _write_summary(summary_path, [_artifact_to_summary(artifact) for artifact in artifacts])
    print(f"Matrix runs: {len(artifacts)}")
    print(f"Simulation result CSV: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
