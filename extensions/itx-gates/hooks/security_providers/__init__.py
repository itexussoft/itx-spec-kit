"""Security provider registry and settings resolver for deterministic SAST."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from validators import Finding

from security_providers import bandit_provider, noop_provider, semgrep_provider


DEFAULT_SECURITY_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "provider": "noop",
    "on_missing_binary": "warn",
    "compat_heuristic_fallback": False,
}

DEFAULT_DOMAIN_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "fintech-banking": {
        "enabled": True,
        "provider": "semgrep",
        "on_missing_binary": "warn",
        "compat_heuristic_fallback": True,
    }
}


def _read_yaml_mapping(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
            continue
        merged[key] = value
    return merged


def resolve_security_settings(workspace: Path, domain: str) -> Dict[str, Any]:
    settings = _merge(DEFAULT_SECURITY_SETTINGS, DEFAULT_DOMAIN_OVERRIDES.get(domain, {}))

    policy = _read_yaml_mapping(workspace / ".specify" / "policy.yml")
    policy_quality = policy.get("quality") if isinstance(policy.get("quality"), dict) else {}
    policy_security = policy_quality.get("security") if isinstance(policy_quality, dict) else {}
    if isinstance(policy_security, dict):
        global_security = {k: v for k, v in policy_security.items() if k != "domains"}
        settings = _merge(settings, global_security)
        domain_overrides = policy_security.get("domains")
        if isinstance(domain_overrides, dict):
            domain_cfg = domain_overrides.get(domain)
            if isinstance(domain_cfg, dict):
                settings = _merge(settings, domain_cfg)

    config = _read_yaml_mapping(workspace / ".itx-config.yml")
    config_security = config.get("security")
    if isinstance(config_security, dict):
        global_security = {k: v for k, v in config_security.items() if k != "domains"}
        settings = _merge(settings, global_security)
        domain_overrides = config_security.get("domains")
        if isinstance(domain_overrides, dict):
            domain_cfg = domain_overrides.get(domain)
            if isinstance(domain_cfg, dict):
                settings = _merge(settings, domain_cfg)

    if "provider" in settings:
        settings["provider"] = str(settings.get("provider", "noop")).strip().lower() or "noop"
    if "enabled" in settings:
        settings["enabled"] = bool(settings.get("enabled"))
    settings["domain"] = domain
    return settings


def run_security_provider(workspace: Path, domain: str) -> List[Finding]:
    settings = resolve_security_settings(workspace, domain)
    if not settings.get("enabled", False):
        return []
    provider = str(settings.get("provider", "noop")).strip().lower() or "noop"
    if provider == "semgrep":
        return semgrep_provider.run(workspace, settings)
    if provider == "bandit":
        return bandit_provider.run(workspace, settings)
    if provider == "noop":
        return noop_provider.run(workspace, settings)
    return [
        {
            "severity": "tier1",
            "rule": "sast-provider-unknown",
            "message": f"Unknown security provider '{provider}'.",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        }
    ]

