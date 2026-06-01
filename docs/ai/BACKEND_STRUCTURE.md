# BACKEND STRUCTURE

## Data Model

- `SimulationConfig`: seed, round count, demand parameters, reputation parameters, cost parameters, action grids.
- `AgentState`: inventory, reputation, last price, last profit, shortage state, and cumulative payoff.
- `SettlementRow`: one long-form record per agent per round.
- `SimulationResult`: records plus summary statistics and artifact paths.

## Tables and Columns

### SettlementRow

- `seed`
- `round`
- `agent_name`
- `agent_role`
- `demand_true`
- `demand_obs`
- `price`
- `quantity`
- `allocated_demand`
- `realized_sales`
- `shortage_post_transfer`
- `inventory_end`
- `reputation_end`
- `profit`
- `cum_profit`

### AgentState

- `inventory`
- `reputation`
- `last_price`
- `last_profit`

## Relationships

- One simulation has many rounds.
- One round has one record per agent.
- One environment step reads all agent actions before writing all agent outcomes.
- One result bundle points to one CSV and zero or more figure files.

## Authentication and Authorization

- None. The simulator is local and single-user by design.

## API Contracts

- `Agent.decide(observation) -> AgentAction`
- `MarketEnvironment.step(actions) -> SettlementRow[]`
- `run_simulation(config) -> SimulationResult`
- `write_rows_to_csv(records, path) -> None`
- `create_summary_figure(records, path) -> None`

## Validation and Error Handling

- Clamp invalid prices and quantities to the nearest legal action.
- Replace malformed agent output with a safe fallback action.
- Reject missing mandatory config fields before simulation starts.
- Keep CSV schema stable across runs.
