from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from .agents import MarketObservation, build_agents
from .config import SimulationConfig, default_simulation_config
from .environment import MarketEnvironment, SettlementRow, write_rows_to_csv
from .timeseries import DemandSeriesGenerator
from .utils import rolling_mean, rolling_volatility
from .visualization import create_summary_figure


@dataclass(frozen=True)
class SimulationResult:
    rows: list[SettlementRow]
    csv_path: Path
    figure_path: Path | None


def _build_observation(
    *,
    agent_name: str,
    round_index: int,
    snapshot_observed: int,
    demand_history: list[int],
    observed_history: list[int],
    price_history: list[list[float]],
    reputation_history: list[list[float]],
    current_reputations: dict[str, float],
    env: MarketEnvironment,
) -> MarketObservation:
    prices_flat = [price for round_prices in price_history for price in round_prices]
    avg_price = mean(prices_flat) if prices_flat else mean(agent.base_price for agent in env.agent_configs.values())
    volatility = rolling_volatility(observed_history, window=5)
    state = env.states[agent_name]
    return MarketObservation(
        round_index=round_index,
        observed_demand=snapshot_observed,
        demand_history=tuple(demand_history),
        observed_demand_history=tuple(observed_history),
        price_history=tuple(tuple(round_prices) for round_prices in price_history),
        reputation_history=tuple(tuple(round_reputations) for round_reputations in reputation_history),
        peer_reputations=tuple(sorted(current_reputations.items())),
        own_inventory=state.inventory,
        own_last_profit=state.last_profit,
        own_last_shortage=state.last_shortage,
        own_reputation=state.reputation,
        market_avg_price=avg_price,
        market_volatility=volatility,
    )


def run_simulation(
    config: SimulationConfig | None = None,
    *,
    output_dir: str | Path | None = None,
    generate_figure: bool = True,
) -> SimulationResult:
    config = config or default_simulation_config()
    effective_output_dir = Path(output_dir or config.output_dir)
    effective_output_dir.mkdir(parents=True, exist_ok=True)

    generator = DemandSeriesGenerator(config.market, seed=config.seed)
    env = MarketEnvironment(config)
    agents = build_agents(config.agents, mode=config.agent_mode, llm_config=config.llm)
    rows: list[SettlementRow] = []
    demand_history: list[int] = []
    observed_history: list[int] = []
    price_history: list[list[float]] = []
    reputation_history: list[list[float]] = []

    for round_index in range(config.rounds):
        snapshot = generator.step(round_index)
        current_reputations = {name: state.reputation for name, state in env.states.items()}
        actions = {}
        for name, agent in agents.items():
            observation = _build_observation(
                agent_name=name,
                round_index=round_index,
                snapshot_observed=snapshot.observed_demand,
                demand_history=demand_history,
                observed_history=observed_history,
                price_history=price_history,
                reputation_history=reputation_history,
                current_reputations=current_reputations,
                env=env,
            )
            actions[name] = agent.decide(observation)
        round_rows = env.step(
            seed=config.seed,
            round_index=round_index,
            snapshot=snapshot,
            actions=actions,
        )
        rows.extend(round_rows)
        demand_history.append(snapshot.true_demand)
        observed_history.append(snapshot.observed_demand)
        price_history.append([actions[name].price for name in agents])
        reputation_history.append([env.states[name].reputation for name in agents])

    csv_path = effective_output_dir / "simulation_results.csv"
    write_rows_to_csv(rows, csv_path)
    figure_path: Path | None = None
    if generate_figure:
        figure_path = effective_output_dir / "strategy_analysis.pdf"
        create_summary_figure(rows, figure_path)
    return SimulationResult(rows=rows, csv_path=csv_path, figure_path=figure_path)
