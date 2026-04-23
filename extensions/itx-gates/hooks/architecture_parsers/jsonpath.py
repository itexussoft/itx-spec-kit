"""Small JSON-path style helpers used by generic architecture adapters."""

from __future__ import annotations

from typing import Any, List


def _split_tokens(expr: str) -> List[str]:
    expression = expr.strip()
    if expression.startswith("$"):
        expression = expression[1:]
    if expression.startswith("."):
        expression = expression[1:]
    if not expression:
        return []

    tokens: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in expression:
        if ch == "." and depth == 0:
            token = "".join(current).strip()
            if token:
                tokens.append(token)
            current = []
            continue
        if ch == "[":
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
        current.append(ch)
    final = "".join(current).strip()
    if final:
        tokens.append(final)
    return tokens


def _descend(nodes: List[Any], token: str) -> List[Any]:
    if token == "*":
        results: List[Any] = []
        for node in nodes:
            if isinstance(node, list):
                results.extend(node)
            elif isinstance(node, dict):
                results.extend(node.values())
        return results

    if token.endswith("[*]"):
        prefix = token[:-3]
        next_nodes: List[Any] = []
        for node in nodes:
            source: Any = node
            if prefix:
                if not isinstance(node, dict):
                    continue
                source = node.get(prefix)
            if isinstance(source, list):
                next_nodes.extend(source)
        return next_nodes

    if token.endswith("]") and "[" in token:
        key, _, index_raw = token.partition("[")
        index_part = index_raw[:-1].strip()
        try:
            index = int(index_part)
        except ValueError:
            return []
        selected: List[Any] = []
        for node in nodes:
            source: Any = node
            if key:
                if not isinstance(node, dict):
                    continue
                source = node.get(key)
            if isinstance(source, list) and 0 <= index < len(source):
                selected.append(source[index])
        return selected

    selected: List[Any] = []
    for node in nodes:
        if isinstance(node, dict) and token in node:
            selected.append(node[token])
    return selected


def resolve_all(payload: Any, expr: str) -> List[Any]:
    tokens = _split_tokens(expr)
    nodes: List[Any] = [payload]
    for token in tokens:
        nodes = _descend(nodes, token)
        if not nodes:
            break
    return nodes


def resolve_first(payload: Any, expr: str) -> Any:
    values = resolve_all(payload, expr)
    return values[0] if values else None

