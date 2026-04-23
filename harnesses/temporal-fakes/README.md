# Temporal Fakes Harness

This scaffold provides a lightweight, language-agnostic pattern for stateful local fakes that
model temporal behavior of real systems.

## What this is
- A small reusable harness under `harnesses/temporal-fakes/`.
- A reference fake service (`example-fake/fake_deployment.py`) with time-based transitions.
- A scenario registry (`scenarios.yaml`) validated by `scenarios.schema.json`.
- Optional local orchestration via `process-compose.yaml`.

## What this is not
- Not a full simulator platform.
- Not provider-specific CDC or Pact infrastructure.
- Not coupled to a specific agent stack or MCP runtime.

## Fidelity patterns
1. Contract tests: run the same contract suite against fake and real service.
2. Consumer-driven contracts: use when fake stands in for a provider API with multiple consumers.
3. Self-initializing fake / record-replay: bootstrap fixtures quickly from observed traffic.
4. Shadow / dual-run testing: mirror requests to fake and compare drift signals.

## Quickstart
1. Run the fake:
   `python harnesses/temporal-fakes/example-fake/fake_deployment.py --port 8080`
2. Trigger a deployment:
   `curl -X POST http://127.0.0.1:8080/deploy`
3. Inject a fault:
   `curl -X POST http://127.0.0.1:8080/scenarios/inject -H 'content-type: application/json' -d '{"id":"degrade-error-rate","type":"degrade","params":{"error_rate":0.3},"duration_s":60}'`
4. Inspect state:
   `curl http://127.0.0.1:8080/state`

## API
- `GET /state` -> `{state, since_ms, metrics:{replicas_ready,error_rate}}`
- `POST /deploy`
- `POST /scenarios/inject` body `{id,type,params,duration_s,start_after_s?,ramp_up_s?}`
- `POST /scenarios/clear`
- `GET /scenarios`
- `GET /healthz`

## Design rules
- Keep state machine logic independent from HTTP transport where possible.
- Inject clock/time in tests; avoid hard wall-clock coupling.
- Keep scenario registry bounded and reviewed like source code.
- Validate scenario data before running local test workflows.
