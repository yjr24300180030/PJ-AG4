from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator
from urllib.parse import parse_qs, urlencode, urlparse

from .agents import build_agents
from .config import SimulationConfig, default_simulation_config
from .core import SimulationRuntime
from .dashboard import build_dashboard_payload, render_dashboard_html
from .data.observation import ObservationBuilder
from .environment import MarketEnvironment, SettlementRow
from .timeseries import DemandSeriesGenerator, DemandSnapshot

LOCAL_LLM_BASE_URL = "http://127.0.0.1:8045/v1"
LOCAL_LLM_API_KEY = "local-dev-key"
LOCAL_LLM_MODEL = "gemini-3-flash"


@dataclass(frozen=True)
class WebOptions:
    seed: int
    rounds: int
    agent_mode: str
    shock_scale: float
    demand_bias: int
    llm_base_url: str | None
    llm_api_key: str | None
    llm_model: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PJ-AG4 localhost dashboard service")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    parser.add_argument("--rounds", type=int, default=30, help="Default number of simulation rounds")
    parser.add_argument("--seed", type=int, default=7, help="Default random seed")
    parser.add_argument("--agent-mode", choices=("heuristic", "llm"), default="heuristic", help="Default policy backend")
    parser.add_argument("--llm-base-url", type=str, default=None, help="OpenAI-compatible base URL for LLM mode")
    parser.add_argument("--llm-api-key", type=str, default=None, help="API key for LLM mode")
    parser.add_argument("--llm-model", type=str, default=None, help="Model name for LLM mode")
    return parser


def _coerce_int(query: dict[str, list[str]], key: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = query.get(key, [str(default)])[0]
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _coerce_mode(query: dict[str, list[str]], default: str) -> str:
    raw = query.get("agent_mode", [default])[0]
    return raw if raw in {"heuristic", "llm"} else default


def _coerce_float(query: dict[str, list[str]], key: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = query.get(key, [str(default)])[0]
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def resolve_options(query: dict[str, list[str]], defaults: WebOptions) -> WebOptions:
    options = WebOptions(
        seed=_coerce_int(query, "seed", defaults.seed, minimum=0, maximum=999999),
        rounds=_coerce_int(query, "rounds", defaults.rounds, minimum=1, maximum=365),
        agent_mode=_coerce_mode(query, defaults.agent_mode),
        shock_scale=_coerce_float(query, "shock_scale", defaults.shock_scale, minimum=-2.0, maximum=2.0),
        demand_bias=_coerce_int(query, "demand_bias", defaults.demand_bias, minimum=-40, maximum=40),
        llm_base_url=query.get("llm_base_url", [defaults.llm_base_url or ""])[0] or defaults.llm_base_url,
        llm_api_key=query.get("llm_api_key", [defaults.llm_api_key or ""])[0] or defaults.llm_api_key,
        llm_model=query.get("llm_model", [defaults.llm_model or ""])[0] or defaults.llm_model,
    )
    if options.agent_mode != "llm":
        return options
    return WebOptions(
        seed=options.seed,
        rounds=options.rounds,
        agent_mode=options.agent_mode,
        shock_scale=options.shock_scale,
        demand_bias=options.demand_bias,
        llm_base_url=options.llm_base_url or LOCAL_LLM_BASE_URL,
        llm_api_key=options.llm_api_key or LOCAL_LLM_API_KEY,
        llm_model=options.llm_model or LOCAL_LLM_MODEL,
    )


def build_config(options: WebOptions, *, rounds: int | None = None) -> SimulationConfig:
    return default_simulation_config(
        seed=options.seed,
        rounds=rounds if rounds is not None else options.rounds,
        output_dir=Path("outputs") / "web_runtime",
        agent_mode=options.agent_mode,
        llm_base_url=options.llm_base_url,
        llm_api_key=options.llm_api_key,
        llm_model=options.llm_model,
    )


def build_runtime_payload(options: WebOptions, *, limit_rounds: int | None = None) -> dict[str, object]:
    rounds = options.rounds if limit_rounds is None else max(1, min(options.rounds, limit_rounds))
    payloads = list(iter_runtime_payloads(options, start_round=0, total_rounds=rounds))
    return payloads[-1]


def run_simulation_rows(config: SimulationConfig, *, strategy_name: str) -> list[object]:
    runtime = SimulationRuntime(config)
    agents = build_agents(
        config.agents,
        mode=strategy_name,
        llm_config=config.llm,
    )
    return runtime.run(agents)


def _apply_runtime_controls(
    snapshot: DemandSnapshot,
    *,
    shock_scale: float,
    demand_bias: int,
    demand_floor: int,
    shock_magnitude: float,
) -> DemandSnapshot:
    manual_shock = abs(shock_magnitude) * shock_scale
    adjusted_shock = snapshot.shock_component + manual_shock
    true_demand = int(
        round(
            max(
                demand_floor,
                snapshot.trend_component
                + snapshot.seasonal_component
                + adjusted_shock
                + snapshot.noise_component
                + demand_bias,
            )
        )
    )
    observed_gap = snapshot.observed_demand - snapshot.true_demand
    observed_demand = int(round(max(demand_floor, true_demand + observed_gap)))
    return DemandSnapshot(
        round_index=snapshot.round_index,
        true_demand=true_demand,
        observed_demand=observed_demand,
        trend_component=snapshot.trend_component,
        seasonal_component=snapshot.seasonal_component,
        shock_component=adjusted_shock,
        noise_component=snapshot.noise_component,
    )


def _attach_runtime_controls(payload: dict[str, object], options: WebOptions) -> dict[str, object]:
    payload["controls"] = {
        "shockScale": options.shock_scale,
        "demandBias": options.demand_bias,
    }
    market = payload.get("market")
    if isinstance(market, dict):
        market["projectedDemand"] = list(market.get("demand", []))
    return payload


def iter_runtime_payloads(
    options: WebOptions,
    *,
    start_round: int = 0,
    total_rounds: int | None = None,
) -> Iterator[dict[str, object]]:
    config = build_config(options, rounds=total_rounds)
    agents = build_agents(
        config.agents,
        mode=options.agent_mode,
        llm_config=config.llm,
    )
    generator = DemandSeriesGenerator(config.market, seed=config.seed)
    env = MarketEnvironment(config)
    observations = ObservationBuilder(env, window=config.market.demand_window)
    rows: list[SettlementRow] = []

    for round_index in range(config.rounds):
        snapshot = _apply_runtime_controls(
            generator.step(round_index),
            shock_scale=options.shock_scale,
            demand_bias=options.demand_bias,
            demand_floor=config.market.demand_floor,
            shock_magnitude=config.market.shock_magnitude,
        )
        current_reputations = {name: state.reputation for name, state in env.states.items()}
        actions = {}
        for name, agent in agents.items():
            observation = observations.build(
                agent_name=name,
                round_index=round_index,
                observed_demand=snapshot.observed_demand,
                current_reputations=current_reputations,
            )
            actions[name] = agent.decide(observation)
        round_rows = env.step(
            seed=config.seed,
            round_index=round_index,
            snapshot=snapshot,
            actions=actions,
        )
        rows.extend(round_rows)
        observations.record_round(snapshot=snapshot, actions=actions)
        if round_index < start_round:
            continue
        payload = build_dashboard_payload(rows, config=config, strategy_name=options.agent_mode)
        yield _attach_runtime_controls(payload, options)


def build_dashboard_page(options: WebOptions) -> str:
    payload = build_runtime_payload(options, limit_rounds=1)
    query = urlencode(
        {
            "seed": options.seed,
            "rounds": options.rounds,
            "agent_mode": options.agent_mode,
            "shock_scale": options.shock_scale,
            "demand_bias": options.demand_bias,
        }
    )
    web_runtime_panel = f"""
              <form class="runtime-panel" id="runtime-form" method="get" action="/">
                <div class="runtime-grid">
                  <label class="runtime-field" for="runtime-seed">
                    <span class="runtime-label">Seed</span>
                    <input id="runtime-seed" class="terminal-select" name="seed" type="number" min="0" max="999999" value="{options.seed}" />
                  </label>
                  <label class="runtime-field" for="runtime-rounds">
                    <span class="runtime-label">Rounds</span>
                    <input id="runtime-rounds" class="terminal-select" name="rounds" type="number" min="1" max="365" value="{options.rounds}" />
                  </label>
                  <label class="runtime-field" for="runtime-agent-mode">
                    <span class="runtime-label">Agent mode</span>
                    <select id="runtime-agent-mode" class="terminal-select" name="agent_mode">
                      <option value="heuristic"{" selected" if options.agent_mode == "heuristic" else ""}>heuristic</option>
                      <option value="llm"{" selected" if options.agent_mode == "llm" else ""}>llm</option>
                    </select>
                  </label>
                </div>
                <div class="runtime-actions">
                  <button type="submit" class="terminal-button active" id="runtime-run">Run stream</button>
                  <a class="terminal-button" id="runtime-json-link" href="/api/payload?{query}" target="_blank" rel="noreferrer">Open JSON payload</a>
                  <span class="status-tag status-neutral" id="runtime-status">boot</span>
                </div>
                <input type="hidden" name="llm_base_url" value="{escape_attr(options.llm_base_url or '')}" />
                <input type="hidden" name="llm_api_key" value="{escape_attr(options.llm_api_key or '')}" />
                <input type="hidden" name="llm_model" value="{escape_attr(options.llm_model or '')}" />
              </form>
    """.strip()
    return render_dashboard_html(
        payload,
        body_class="web-runtime-active",
        web_runtime_panel=web_runtime_panel,
    )


def make_handler(defaults: WebOptions) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            options = resolve_options(query, defaults)
            try:
                if parsed.path in {"", "/", "/dashboard"}:
                    body = build_dashboard_page(options).encode("utf-8")
                    self._send_bytes(body, content_type="text/html; charset=utf-8")
                    return

                if parsed.path == "/api/payload":
                    limit_rounds = _coerce_int(query, "limit_rounds", options.rounds, minimum=1, maximum=options.rounds)
                    use_limit = limit_rounds if "limit_rounds" in query else None
                    body = json.dumps(build_runtime_payload(options, limit_rounds=use_limit), ensure_ascii=False).encode("utf-8")
                    self._send_bytes(body, content_type="application/json; charset=utf-8")
                    return

                if parsed.path == "/api/stream":
                    start_round = _coerce_int(query, "start_round", 0, minimum=0, maximum=max(0, options.rounds - 1))
                    self._send_stream(iter_runtime_payloads(options, start_round=start_round))
                    return

                if parsed.path == "/health":
                    self._send_bytes(b'{"ok":true}', content_type="application/json; charset=utf-8")
                    return

                self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            except Exception as exc:
                self._send_error_response(parsed.path, exc)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _send_bytes(self, body: bytes, *, content_type: str) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_stream(self, payloads: Iterator[dict[str, object]]) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Connection", "close")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                for payload in payloads:
                    message = "event: round\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
                    self.wfile.write(message.encode("utf-8"))
                    self.wfile.flush()
                self.wfile.write(b"event: done\ndata: {}\n\n")
                self.wfile.flush()
                self.close_connection = True
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:
                message = "event: stream_error\ndata: " + json.dumps({"error": str(exc)}, ensure_ascii=False) + "\n\n"
                self.wfile.write(message.encode("utf-8"))
                self.wfile.write(b"event: done\ndata: {}\n\n")
                self.wfile.flush()
                self.close_connection = True

        def _send_error_response(self, path: str, exc: Exception) -> None:
            body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
            status = HTTPStatus.BAD_REQUEST if path.startswith("/api/") else HTTPStatus.INTERNAL_SERVER_ERROR
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def escape_attr(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    defaults = WebOptions(
        seed=args.seed,
        rounds=args.rounds,
        agent_mode=args.agent_mode,
        shock_scale=0.0,
        demand_bias=0,
        llm_base_url=args.llm_base_url,
        llm_api_key=args.llm_api_key,
        llm_model=args.llm_model,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(defaults))
    print(f"PJ-AG4 dashboard server running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
