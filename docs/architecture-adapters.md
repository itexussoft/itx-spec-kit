# Architecture Adapters

This document describes Wave F architecture assurance adapters for `itx-gates`.

## Runners

- `generic`: execute a configured command and parse SARIF 2.1.0, JUnit XML, or mapped JSON.
- `spectral`: run `spectral lint -f sarif --fail-severity=none` against configured API spec files.
- `archunit`: run a JVM test command and parse JUnit XML failures (for example Surefire reports).
- `modulith`: read a JSON report emitted by a custom Spring Modulith verification wrapper.

## Policy Example

```yaml
quality:
  architecture:
    enabled: true
    mode: advisory
    runner: generic
    command: ["depcruise", "src", "-T", "err-json"]
    parse:
      format: json
      iterate: "$.summary.violations[*]"
      map:
        rule_id: "rule.name"
        severity: "rule.severity"
        file: "from"
        message: "comment"
```

## Baseline Flow

1. Run `after_implement` to generate `.specify/context/architecture-report.json`.
2. Freeze current findings with:

```bash
python extensions/itx-gates/hooks/gatectl.py baseline-update --kind architecture --workspace .
```

3. Re-run gates. Baseline matches are marked as pre-existing and stay Tier 1.

## Polyglot Adapter Notes

- `dependency-cruiser` (`-T err-json`) maps cleanly through `generic` JSON mapping.
- `import-linter` can be wrapped with a small JSON-emitting shim and consumed through `generic`.
- `depguard`/`golangci-lint` SARIF output can be consumed via SARIF parsing.
- `PyTestArch`/`Konsist` JUnit XML reports can be consumed via JUnit parsing.

