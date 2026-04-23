# Optional MCP Adapter Sketch

This harness does not ship MCP runtime code. This note shows a minimal integration shape for
teams that want scenario injection as a tool endpoint.

## Idea
- Keep the fake service unchanged (`/scenarios/inject`, `/scenarios/clear`, `/scenarios`).
- Expose thin MCP tools that forward requests to the fake over HTTP.
- Return normalized JSON responses with explicit success/error fields.

## Example tool surface
- `temporal_fake_inject(id, type, params, duration_s, start_after_s?, ramp_up_s?)`
- `temporal_fake_clear()`
- `temporal_fake_list()`
- `temporal_fake_state()`

## Minimal Python sketch
```python
import json
import urllib.request

BASE = "http://127.0.0.1:8080"

def _post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))

def inject(id: str, fault_type: str, params: dict, duration_s: int) -> dict:
    return _post("/scenarios/inject", {"id": id, "type": fault_type, "params": params, "duration_s": duration_s})
```

## Guardrails
- Keep adapter stateless and deterministic.
- Validate input shape before HTTP call.
- Avoid embedding scenario DSL logic into the MCP layer.
- Treat scenario ids as stable identifiers for observability.
