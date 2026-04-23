"""Deterministic mapping from rule identifiers to refactoring guidance."""

from __future__ import annotations

import re
from typing import Dict, List, Optional


_RULE_PATTERNS: List[Dict[str, str]] = [
    {"pattern": r"(cycle|circular|cyclic)", "pattern_name": "Dependency Inversion / Mediator", "anti_pattern": "Cyclic Dependency"},
    {"pattern": r"(god|large-class|too-many-methods)", "pattern_name": "Extract Class / Extract Subclass", "anti_pattern": "God Class"},
    {"pattern": r"(feature-envy|law-of-demeter)", "pattern_name": "Move Function", "anti_pattern": "Feature Envy"},
    {
        "pattern": r"(shotgun|divergent-change)",
        "pattern_name": "Combine Functions into Class",
        "anti_pattern": "Shotgun Surgery / Divergent Change",
    },
    {"pattern": r"(data-clump|too-many-parameters)", "pattern_name": "Introduce Parameter Object", "anti_pattern": "Data Clumps"},
    {"pattern": r"(layer-violation|forbidden-import)", "pattern_name": "Dependency Inversion / Facade", "anti_pattern": "Layer Leak"},
    {"pattern": r"(inappropriate-intimacy)", "pattern_name": "Hide Delegate / Move Method", "anti_pattern": "Inappropriate Intimacy"},
    {"pattern": r"(message-chain)", "pattern_name": "Hide Delegate", "anti_pattern": "Law of Demeter violation"},
    {
        "pattern": r"(refused-bequest)",
        "pattern_name": "Push Down Method / Replace Inheritance with Delegation",
        "anti_pattern": "Refused Bequest",
    },
]


def map_rule_to_pattern(rule_id: str) -> Dict[str, Optional[str] | bool]:
    normalized = rule_id.strip().lower()
    for rule in _RULE_PATTERNS:
        if re.search(rule["pattern"], normalized):
            return {
                "matched": True,
                "pattern": rule["pattern_name"],
                "anti_pattern": rule["anti_pattern"],
                "reference": "https://refactoring.com/catalog/",
            }
    return {
        "matched": False,
        "pattern": None,
        "anti_pattern": None,
        "reference": "https://refactoring.com/catalog/",
    }

