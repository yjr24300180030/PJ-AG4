# BACKEND STRUCTURE

## Data Model

- `SimulationConfig`: seed, round count, demand parameters, reputation parameters, cost parameters, action grids.
- `AgentState`: inventory, cash, reputation, last price, last quantity, cumulative payoff.
- `RoundRecord`: one long-form record per agent per round.
- `SimulationResult`: records plus summary statistics and artifact paths.

## Tables and Columns

### RoundRecord

- `seed`
- `round`
- `agent_id`
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
- `cash`
- `reputation`
- `last_price`
- `last_quantity`
- `last_profit`

## Relationships

- One simulation has many rounds.
- One round has one record per agent.
- One environment step reads all agent actions before writing all agent outcomes.
- One result bundle points to one CSV and zero or more figure files.

## Authentication and Authorization

- None. The simulator is local and single-user by design.

## API Contracts

- `Agent.act(observation) -> Action`
- `Environment.step(actions) -> RoundRecord[]`
- `run_simulation(config) -> SimulationResult`
- `export_csv(records, path) -> None`
- `plot_results(records, path) -> list[path]`

## Validation and Error Handling

- Clamp invalid prices and quantities to the nearest legal action.
- Replace malformed agent output with a safe fallback action.
- Reject missing mandatory config fields before simulation starts.
- Keep CSV schema stable across runs.
