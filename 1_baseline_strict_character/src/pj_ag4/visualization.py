from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .environment import SettlementRow


def create_summary_figure(rows: list[SettlementRow], output_path: Path) -> None:
    if not rows:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rounds = sorted({row.round for row in rows})
    agent_names = sorted({row.agent_name for row in rows})
    demand_by_round = {round_index: next(row.demand_true for row in rows if row.round == round_index) for round_index in rounds}
    cumulative_profit = defaultdict(list)
    current_profit = {name: 0.0 for name in agent_names}
    for round_index in rounds:
        round_rows = [row for row in rows if row.round == round_index]
        for row in round_rows:
            current_profit[row.agent_name] = row.cum_profit
        for name in agent_names:
            cumulative_profit[name].append(current_profit[name])

    fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    axes[0].plot(rounds, [demand_by_round[r] for r in rounds], color="#1f77b4", linewidth=2.2, label="True demand")
    axes[0].set_ylabel("Demand")
    axes[0].set_title("Market demand and cumulative profit")
    axes[0].legend(loc="upper left")

    for name in agent_names:
        axes[1].plot(rounds, cumulative_profit[name], linewidth=2.0, label=name)
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("Cumulative profit")
    axes[1].legend(loc="upper left")
    axes[1].grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)

