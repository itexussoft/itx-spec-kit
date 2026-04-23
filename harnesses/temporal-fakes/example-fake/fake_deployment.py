#!/usr/bin/env python3
"""Stateful deployment fake with temporal transitions and fault injection."""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List


Clock = Callable[[], float]


@dataclass
class Injection:
    scenario_id: str
    fault_type: str
    params: Dict[str, Any]
    created_at: float
    start_at: float
    end_at: float
    ramp_up_s: float = 0.0

    def is_active(self, now: float) -> bool:
        return self.start_at <= now < self.end_at

    def remaining_s(self, now: float) -> int:
        return max(0, int(self.end_at - now))


class DeploymentFake:
    def __init__(self, clock: Clock | None = None) -> None:
        self._clock: Clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._state = "idle"
        self._state_since = self._clock()
        self._deploy_started_at: float | None = None
        self._ever_deployed = False
        self._injections: List[Injection] = []

    def _now(self) -> float:
        return self._clock()

    def _set_state(self, next_state: str, now: float) -> None:
        if self._state != next_state:
            self._state = next_state
            self._state_since = now

    def deploy(self) -> Dict[str, Any]:
        with self._lock:
            now = self._now()
            self._deploy_started_at = now
            self._ever_deployed = True
            self._set_state("deploying", now)
            return {"ok": True, "state": self._state}

    def inject(
        self,
        *,
        scenario_id: str,
        fault_type: str,
        params: Dict[str, Any] | None,
        duration_s: int,
        start_after_s: int = 0,
        ramp_up_s: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            now = self._now()
            injection = Injection(
                scenario_id=scenario_id,
                fault_type=fault_type,
                params=params or {},
                created_at=now,
                start_at=now + max(0, int(start_after_s)),
                end_at=now + max(1, int(start_after_s) + int(duration_s)),
                ramp_up_s=max(0, int(ramp_up_s)),
            )
            self._injections.append(injection)
            return {"ok": True, "scenario": scenario_id}

    def clear(self) -> Dict[str, Any]:
        with self._lock:
            self._injections.clear()
            now = self._now()
            if self._state != "deploying":
                self._set_state("healthy" if self._ever_deployed else "idle", now)
            return {"ok": True}

    def _active_injections(self, now: float) -> List[Injection]:
        self._injections = [inj for inj in self._injections if inj.end_at > now]
        return [inj for inj in self._injections if inj.is_active(now)]

    def tick(self) -> None:
        with self._lock:
            now = self._now()
            active = self._active_injections(now)

            if self._state == "deploying" and self._deploy_started_at is not None:
                if now - self._deploy_started_at >= 30:
                    self._set_state("healthy", now)

            fail_injection = next((inj for inj in active if inj.fault_type == "fail"), None)
            degrade_injection = next((inj for inj in active if inj.fault_type == "degrade"), None)

            if fail_injection is not None:
                self._set_state("failed", now)
                return
            if degrade_injection is not None:
                self._set_state("degraded", now)
                return
            if self._state != "deploying":
                self._set_state("healthy" if self._ever_deployed else "idle", now)

    def _metrics(self, now: float) -> Dict[str, Any]:
        active = self._active_injections(now)
        fail_injection = next((inj for inj in active if inj.fault_type == "fail"), None)
        degrade_injection = next((inj for inj in active if inj.fault_type == "degrade"), None)
        if fail_injection is not None:
            return {"replicas_ready": 0, "error_rate": 1.0}
        if degrade_injection is not None:
            target = float(degrade_injection.params.get("error_rate", 0.3))
            return {"replicas_ready": 2, "error_rate": max(0.0, min(1.0, target))}
        if self._state == "deploying":
            return {"replicas_ready": 1, "error_rate": 0.0}
        if self._state == "failed":
            return {"replicas_ready": 0, "error_rate": 1.0}
        return {"replicas_ready": 3 if self._state == "healthy" else 0, "error_rate": 0.0}

    def snapshot(self) -> Dict[str, Any]:
        self.tick()
        with self._lock:
            now = self._now()
            return {
                "state": self._state,
                "since_ms": int((now - self._state_since) * 1000),
                "metrics": self._metrics(now),
            }

    def scenarios(self) -> List[Dict[str, Any]]:
        with self._lock:
            now = self._now()
            active = self._active_injections(now)
            return [
                {
                    "id": inj.scenario_id,
                    "type": inj.fault_type,
                    "params": inj.params,
                    "remaining_s": inj.remaining_s(now),
                    "active": inj.is_active(now),
                }
                for inj in active
            ]


class _Handler(BaseHTTPRequestHandler):
    fake: DeploymentFake

    def _json_response(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Dict[str, Any]:
        try:
            raw_len = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raw_len = 0
        raw = self.rfile.read(raw_len) if raw_len > 0 else b"{}"
        try:
            decoded = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            decoded = {}
        return decoded if isinstance(decoded, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/state":
            self._json_response(self.fake.snapshot())
            return
        if self.path == "/scenarios":
            self._json_response({"scenarios": self.fake.scenarios()})
            return
        if self.path == "/healthz":
            self._json_response({"ok": True})
            return
        self._json_response({"ok": False, "error": "not-found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/deploy":
            self._json_response(self.fake.deploy())
            return
        if self.path == "/scenarios/clear":
            self._json_response(self.fake.clear())
            return
        if self.path == "/scenarios/inject":
            payload = self._read_json()
            scenario_id = str(payload.get("id", "adhoc")).strip() or "adhoc"
            fault_type = str(payload.get("type", "degrade")).strip() or "degrade"
            params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
            duration_s = int(payload.get("duration_s", 30))
            start_after_s = int(payload.get("start_after_s", 0))
            ramp_up_s = int(payload.get("ramp_up_s", 0))
            self._json_response(
                self.fake.inject(
                    scenario_id=scenario_id,
                    fault_type=fault_type,
                    params=params,
                    duration_s=duration_s,
                    start_after_s=start_after_s,
                    ramp_up_s=ramp_up_s,
                )
            )
            return
        self._json_response({"ok": False, "error": "not-found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def _ticker(fake: DeploymentFake, stop_event: threading.Event, tick_s: float) -> None:
    while not stop_event.is_set():
        fake.tick()
        stop_event.wait(tick_s)


def _print_example_scenarios() -> None:
    sample = {
        "id": "degrade-error-rate",
        "type": "degrade",
        "params": {"error_rate": 0.3},
        "duration_s": 60,
        "start_after_s": 5,
        "ramp_up_s": 10,
    }
    print(json.dumps(sample, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run temporal deployment fake service")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--tick-ms", type=int, default=1000)
    parser.add_argument("--print-example-scenarios", action="store_true")
    args = parser.parse_args()

    if args.print_example_scenarios:
        _print_example_scenarios()
        return 0

    fake = DeploymentFake()
    _Handler.fake = fake
    server = ThreadingHTTPServer(("127.0.0.1", args.port), _Handler)
    stop_event = threading.Event()
    ticker = threading.Thread(target=_ticker, args=(fake, stop_event, max(0.1, args.tick_ms / 1000.0)), daemon=True)
    ticker.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
