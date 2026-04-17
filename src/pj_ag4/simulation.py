from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .agents import build_agents
from .config import SimulationConfig, default_simulation_config
from .contracts import SimulationResult
from .dashboard import create_dashboard
from .core import SimulationRuntime
from .environment import write_rows_to_csv
from .visualization import create_summary_figure


def run_simulation(
    config: SimulationConfig | None = None,
    *,
    output_dir: str | Path | None = None,
    generate_figure: bool = True,
    generate_dashboard: bool = True,
    strategy_name: str | None = None,
    agents: Mapping[str, Any] | None = None,
) -> SimulationResult:
    config = config or default_simulation_config()
    effective_output_dir = Path(output_dir or config.output_dir)
    effective_output_dir.mkdir(parents=True, exist_ok=True)
    runtime = SimulationRuntime(config)
    resolved_agents = agents
    if resolved_agents is None:
        resolved_agents = build_agents(
            config.agents,
            mode=(strategy_name or config.agent_mode),
            llm_config=config.llm,
        )
    rows = runtime.run(resolved_agents)

    csv_path = effective_output_dir / "simulation_results.csv"
    write_rows_to_csv(rows, csv_path)
    figure_path: Path | None = None
    if generate_figure:
        figure_path = effective_output_dir / "strategy_analysis.pdf"
        create_summary_figure(rows, figure_path)
    dashboard_path: Path | None = None
    if generate_dashboard:
        dashboard_path = effective_output_dir / "strategy_dashboard.html"
        create_dashboard(rows, dashboard_path, config=config, strategy_name=(strategy_name or config.agent_mode))
    return SimulationResult(rows=rows, csv_path=csv_path, figure_path=figure_path, dashboard_path=dashboard_path)
