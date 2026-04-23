# Tech Radar Program — Execution Plan

Date: 2026-04-23
Status: Approved execution plan
Applies to repository: `/Users/sprivalov/itexus/src/itx-spec-kit`
Recommended branch: `itx-tech-radar-program`
Source radar: Thoughtworks Technology Radar Vol. 34 (April 2026)

This document is the working execution plan for adapting `itx-spec-kit` to four strategic
directions inspired by the Tech Radar Vol. 34. It translates the authoritative program plan into
concrete edits against the current codebase and folds in findings from targeted web research.

In case of conflict between this document and informal notes, this document wins. In case of
conflict with the upstream authoritative program plan (the one that reads "this document is the
single source of truth"), that plan wins on scope and non-negotiables; this document wins on
implementation shape.

---

## 1. Tech Radar Vol. 34 framing

The program targets four Radar entries:

- **#17 Architecture drift reduction with LLMs** (Assess) — deterministic tools (Spectral,
  ArchUnit, Spring Modulith) detect violations; LLMs are allowed only in a remediation-assist role.
- **#11 Mutation testing** (Trial) + **#71 cargo-mutants** (Trial) — honest fault-detection
  signal; antidote to "perpetually green" AI-generated tests.
- **#10 Mapping code smells to refactoring techniques** (Trial) — delivered via Agent Skills /
  slash commands / AGENTS.md so agents apply the right refactoring for a detected smell.
- **#31 Temporal fakes** (Assess) — stateful fakes that model the temporal evolution of real
  systems; optional MCP scenario injection; process-compose orchestration.

## 2. Current repository — where each wave lands

| Plan element                 | Current artifact                                               | Integration shape                                                |
|------------------------------|----------------------------------------------------------------|------------------------------------------------------------------|
| Lifecycle dispatch           | `extensions/itx-gates/hooks/orchestrator_runtime.py`           | New runners invoked from existing lifecycle branches              |
| Validator plug-in pattern    | `DOMAIN_VALIDATORS` dict in `orchestrator_common.py`           | Adapter dicts mirror this convention                              |
| Finding shape                | `Finding` TypedDict (severity/rule/message/...)                | Reuse unchanged                                                   |
| Tier system                  | `tier1` retryable / `tier2` blocking (ADR 0002)                | `advisory -> tier1 heuristic`; `strict -> tier2 deterministic`    |
| Persistence                  | `write_gate_state` / `append_gate_event` / summary / feedback  | Reuse unchanged; add new side-artifacts only                      |
| Policy                       | `presets/base/policy.yml`                                      | New `quality.architecture.*`, `quality.mutation_testing.*` blocks |
| Harness convention           | `harnesses/docker-fallbacks/` (compose file only)              | `harnesses/temporal-fakes/` follows same thin scaffold style      |
| Execution-brief enrichment   | `_generate_execution_brief` in `orchestrator_brief.py`         | Wave H1 smell guidance appends a small section                    |
| Build check                  | `make compile` file list in `Makefile`                         | Every new `.py` file must be appended there                       |

`.github/workflows/` is empty. The triplet `make test && make compile && make validate-catalog`
is the only automated safety net during the program.

## 3. Design decisions (research-informed)

### 3.1 Adapter interface

Mirror the existing validator convention so reviewers see one pattern.

```python
# architecture_adapters/__init__.py and mutation_adapters/__init__.py
def run(workspace: Path, config: dict) -> list[Finding]: ...
```

Runners (`architecture_runner.py`, `mutation_runner.py`) own config resolution, adapter selection
(`auto`/named/`generic`), advisory-vs-strict severity mapping, timeout, persistence. Adapters
only invoke the tool and parse output.

### 3.2 Parser priority in the generic command adapter

Relevant ecosystem is fragmented: ArchUnit / PyTestArch / Konsist emit JUnit XML; Spectral /
depguard-via-golangci-lint emit SARIF 2.1.0; dependency-cruiser / Deply / cargo-mutants / Stryker
emit native JSON; Pitest emits non-JUnit XML; import-linter emits text only.

Built-in parsers in the generic adapter, in order of preference:

1. **SARIF 2.1.0** (widest coverage, strict schema).
2. **Stryker mutation-testing-report-schema** (Wave G canonical format).
3. **JUnit XML** (fallback for JVM-test-hosted tools).

Plus a JSONPath-style extractor config knob for proprietary JSON (dependency-cruiser `err-json`,
Deply, `cargo-mutants` `outcomes.json`). Example adapter config:

```yaml
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

No external `jq` dependency — use `jsonpath-ng` (pure Python) or a small internal resolver.

### 3.3 Exit-code contract

Many tools exit 0 with violations present (`spectral --fail-severity=none`, `golangci-lint` v2
dropped `--out-format`). Rule: treat the parsed report as authoritative; treat non-zero exit as a
synthetic finding only if the adapter declares `exit_code_signals: violations` explicitly.

### 3.4 Baseline / freezing from day one

Every Wave-F and Wave-G adapter integrates with a per-project baseline:

- `.specify/context/architecture-baseline.json`
- `.specify/context/mutation-baseline.json`

Findings present in the baseline are demoted to `tier1 advisory` with a `pre-existing` tag; only
new findings participate in strict mode. Mirrors `FreezingArchRule` semantics from ArchUnit.
Without this, Wave F would break the first workspace it enables — the top failure mode in the
literature is triage fatigue from initial scans.

### 3.5 Advisory / strict / tier mapping

- `advisory` -> `tier1` + `confidence: heuristic` + `remediation_owner: feature-team`. Retry-able;
  does not escalate.
- `strict` -> `tier2` + `confidence: deterministic`. Blocking per existing tier2 semantics.
- Baseline findings -> `tier1` regardless of mode.

No new severity level. No new retry class.

### 3.6 Config layering

- Shipped defaults in `presets/base/policy.yml` with `enabled: false`. Existing workspaces
  unaffected.
- Workspace overrides in `.specify/config.yml` under the same `quality.*` namespace. (Final
  filename confirmation is the one open decision — see §10.)
- Verticals (`fintech-trading`, `fintech-banking`, `healthcare`, `saas-platform`) stay silent.

### 3.7 LLM-driven remediation is out-of-scope for this program

Research surfaced iSMELL (ASE 2024) as the closest reference architecture for deterministic-detect
+ LLM-remediate. Implementing it inside `itx-gates` would widen scope. Instead:

- `rule_to_pattern_mapper.py` provides a deterministic static mapping (violation rule ->
  pattern / anti-pattern + one-line fix intent), seeded from `refactoring.com/catalog` and
  Refactoring.Guru.
- Mapped guidance is emitted into `gate_feedback.md` and optionally into `execution-brief.md`.
- The coding agent itself consumes the guidance as context; `itx-gates` does not call an LLM.

Honors authoritative-plan non-negotiable #6 ("no mandatory new runtime dependency on LLM judgment
for correctness").

## 4. Wave F — Architecture Assurance Adapters

### 4.1 Objective

Add deterministic architecture assurance to `itx-gates`, configurable and backward-compatible,
with optional remediation guidance via the rule-to-pattern mapper.

### 4.2 Adapter set

| Adapter                      | Real impl in Wave F? | Notes                                                                                           |
|------------------------------|----------------------|-------------------------------------------------------------------------------------------------|
| `generic_command_adapter.py` | Yes — real           | SARIF / JSON / JUnit XML parsers + JSONPath extractor. Backbone.                                |
| `spectral_adapter.py`        | Yes — real           | Thin wrapper: `spectral lint -f sarif`. API-spec-only; advertise as "contract architecture".    |
| `archunit_adapter.py`        | Stub + docs          | JVM-only, no CLI. Adapter invokes `mvn/gradle test`, parses `surefire-reports/TEST-*.xml`. Ships helper example doc for workspaces. |
| `modulith_adapter.py`        | Stub                 | Spring Modulith has no native JSON output. Docs show `detectViolations()` JSON-serialization.   |
| `polyglot_adapters.md`       | Doc only             | Cookbook mapping `dependency-cruiser`, `import-linter`, `Deply`, `PyTestArch`, `depguard`, `Konsist` onto the generic adapter. |

### 4.3 New and edited files

New files:

- `extensions/itx-gates/hooks/architecture_runner.py`
- `extensions/itx-gates/hooks/architecture_adapters/__init__.py`
- `extensions/itx-gates/hooks/architecture_adapters/generic_command_adapter.py`
- `extensions/itx-gates/hooks/architecture_adapters/spectral_adapter.py`
- `extensions/itx-gates/hooks/architecture_adapters/archunit_adapter.py`
- `extensions/itx-gates/hooks/architecture_adapters/modulith_adapter.py`
- `extensions/itx-gates/hooks/rule_to_pattern_mapper.py`
- `extensions/itx-gates/hooks/architecture_parsers/sarif.py`
- `extensions/itx-gates/hooks/architecture_parsers/junit_xml.py`
- `extensions/itx-gates/hooks/architecture_parsers/jsonpath.py`
- `docs/architecture-adapters.md` (includes `polyglot_adapters.md` content and ArchUnit helper example)

Edits:

- `orchestrator_runtime.py` — call `architecture_runner.run(...)` in the `after_implement` (and
  conditionally `after_plan`) branch; merge findings into the existing tier pipeline.
- `orchestrator_common.py` — extend policy loader to honor `quality.architecture` and workspace
  config overlay.
- `presets/base/policy.yml` — add `quality.architecture.*` block (disabled by default).
- `Makefile` — add new `.py` files to `compile` target.

### 4.4 Rule-to-pattern mapper seed content (~20 entries)

| Rule pattern (substring / regex) | Suggested pattern                                        | Suggested anti-pattern tag        |
|----------------------------------|----------------------------------------------------------|-----------------------------------|
| `cycle`, `circular`, `cyclic`    | Dependency Inversion / Mediator                          | Cyclic Dependency                 |
| `god`, `large-class`, `too-many-methods` | Extract Class / Extract Subclass                 | God Class                         |
| `feature-envy`, `law-of-demeter` | Move Function                                            | Feature Envy                      |
| `shotgun`, `divergent-change`    | Combine Functions into Class                             | Shotgun Surgery / Divergent Change|
| `data-clump`, `too-many-parameters` | Introduce Parameter Object                            | Data Clumps                       |
| `layer-violation`, `forbidden-import` | Dependency Inversion / Facade                       | Layer Leak                        |
| `inappropriate-intimacy`         | Hide Delegate / Move Method                              | Inappropriate Intimacy            |
| `message-chain`                  | Hide Delegate                                            | Law of Demeter violation          |
| `refused-bequest`                | Push Down Method / Replace Inheritance with Delegation   | Refused Bequest                   |

Matching is substring or regex on `rule_id`. Unmatched rules get `pattern: null` and a generic
pointer to `refactoring.com/catalog` — configurable to tier2 via `fail_on_unmapped_violation: true`.

### 4.5 Policy block

```yaml
quality:
  architecture:
    enabled: false
    mode: advisory        # advisory | strict
    runner: auto          # auto | archunit | spectral | modulith | generic
    command: null         # required when runner == generic
    parse: null           # parser spec for generic runner (see §3.2)
    events: [after_implement]   # also supports [after_plan, after_implement]
    baseline_file: .specify/context/architecture-baseline.json
    fail_on_unmapped_violation: false
    exit_code_signals: report   # report | violations
    timeout_s: 120
```

### 4.6 Persistence

Reuse existing `write_gate_state`, `append_gate_event`, `write_last_gate_summary`,
`write_gate_feedback`. New artifacts:

- `.specify/context/architecture-report.json` (SARIF-shaped regardless of source tool).
- `.specify/context/architecture-baseline.json` (written only on explicit
  `gatectl ... --baseline-update` invocation).

### 4.7 Tests

- Parser matrix (SARIF, JUnit XML, custom JSON via JSONPath extractor).
- Baseline filtering.
- Unmapped-rule fallback.
- Advisory vs strict severity mapping.
- Missing-config no-op.
- Timeout handling.

### 4.8 Done criteria

- Architecture capability configurable without breaking default workspaces.
- Generic command adapter works end-to-end.
- Runtime findings persisted through the existing gate-state model.
- Remediation guidance attached in a structured way.
- `make test`, `make compile`, `make validate-catalog` all pass.

## 5. Wave G — Mutation Testing Advisory Rollout

### 5.1 Objective

Add mutation testing in `after_implement` as a behavior-strength signal. Advisory by default,
opt-in strict per module.

### 5.2 Canonical normalization to Stryker schema

`mutation_runner.py` normalizes all adapter outputs into the canonical
`mutation-testing-elements` schema. Each mutant: `{id, mutatorName, location, status,
replacement, killedBy, coveredBy, duration}`.

| Adapter                      | Source format                                    | Normalization |
|------------------------------|--------------------------------------------------|---------------|
| `stryker_adapter.py`         | `reports/mutation/mutation.json`                 | Pass-through  |
| `pitest_adapter.py`          | `target/pit-reports/<ts>/mutations.xml`          | XML -> schema |
| `cargo_mutants_adapter.py`   | `mutants.out/outcomes.json` + `mutants.json`     | JSON -> schema|
| `python_adapter.py`          | `cosmic-ray` JSON or `mutmut junitxml`           | -> schema     |
| `generic_command_adapter.py` | Any schema-conforming JSON                       | Pass-through  |

`python_adapter.py` is prioritized as a real implementation because `itx-spec-kit` itself is
Python-heavy. `mutpy` is abandoned; `cosmic-ray` (mature) and `mutmut` (lightweight) are the live
Python options.

### 5.3 New and edited files

New files:

- `extensions/itx-gates/hooks/mutation_runner.py`
- `extensions/itx-gates/hooks/mutation_adapters/__init__.py`
- `extensions/itx-gates/hooks/mutation_adapters/generic_command_adapter.py`
- `extensions/itx-gates/hooks/mutation_adapters/stryker_adapter.py`
- `extensions/itx-gates/hooks/mutation_adapters/pitest_adapter.py`
- `extensions/itx-gates/hooks/mutation_adapters/cargo_mutants_adapter.py`
- `extensions/itx-gates/hooks/mutation_adapters/python_adapter.py`
- `extensions/itx-gates/hooks/mutation_remediation.py`
- `docs/mutation-remediation.md`

Edits:

- `orchestrator_runtime.py` — call `mutation_runner.run(...)` only in `after_implement`.
- `presets/base/policy.yml` — add `quality.mutation_testing.*` block.
- `Makefile` — register new files.

### 5.4 Policy block

```yaml
quality:
  mutation_testing:
    enabled: false
    mode: advisory
    threshold: 60             # advisory floor (research-supported)
    strict_threshold: 80      # applied only when mode == strict
    runner: auto              # auto | stryker | pitest | cargo-mutants | python | generic
    command: null
    incremental: true         # use tool-native incremental/diff mode where available
    flaky_reruns: 2           # re-runs for surviving mutants; flips -> status_reason: flaky
    ignore_file: .specify/mutation-ignore.yml
    scope: core_modules       # core_modules | all (glob list resolved from policy)
    baseline_file: .specify/context/mutation-baseline.json
    events: [after_implement]
```

### 5.5 Incremental mode — per adapter

- StrykerJS: `--incremental --incrementalFile .specify/context/stryker-incremental.json`.
- Stryker.NET: `--baseline`.
- Pitest: opt-in `scmMutationCoverage` (requires Maven SCM plugin). Not forced.
- cargo-mutants: `--in-diff <pr.diff>` where `pr.diff = git diff $(git merge-base HEAD main)...HEAD`.
- cosmic-ray / mutmut: no first-party incremental; scope via `scope: core_modules` glob.

### 5.6 Behavior-focused remediation vocabulary

Classifier in `mutation_remediation.py` keyed on `mutatorName`:

- Boundary mutators (`ConditionalExpression`, `EqualityOperator`, `MathOp`):
  > "A boundary condition at line N flipped and no test failed. Add a case at the exact boundary
  > value — tests with values 'obviously inside' or 'obviously outside' the range miss this."
- Return-value mutators (`ReturnValue`, `BooleanReturn`):
  > "The mutation changed the concrete return value but your assertion only checks a shape
  > (length/type/truthiness). Assert the actual expected value."
- Void-call mutators (`VoidMethodCalls`, `RemoveCall`):
  > "A side-effecting call was removed and tests still passed. Assert the observable consequence —
  > a spy invocation, a state change, a persisted row — not just that the function returned."
- Mock-boundary mutants:
  > "The mutation is downstream of a mock that returns a constant. Your test is exercising the
  > mock, not the code. Use a fake or assert on the argument passed into the collaborator."
- `NoCoverage` status:
  > "The mutated line has no covering test at all. Before tuning assertions, add a test that
  > executes this branch."

### 5.7 Flaky-mutant suppression

`flaky_reruns: 2` default. Any mutant that flips status between runs is tagged
`status_reason: flaky` and excluded from the score. Matches the Shi et al. UIUC pattern.
`.specify/mutation-ignore.yml` is a workspace-owned manual override list for known-equivalent
mutants.

### 5.8 Persistence

New artifacts:

- `.specify/context/mutation-report.json` (canonical Stryker schema).
- `.specify/context/mutation-summary.md`.
- `.specify/context/mutation-baseline.json` (written only on explicit baseline update).

Mutation outcomes also reflected in `gate-state.yml`, `gate-events.jsonl`, `last-gate-summary.md`.

### 5.9 Tests

- Adapter selection (auto / named / generic).
- Unconfigured workspace: no-op.
- Generic mutation adapter end-to-end (fake `command` emitting schema-valid JSON).
- Threshold comparison (advisory vs strict).
- Flaky-rerun logic.
- Baseline filtering.
- Gate summary integration.
- Remediation vocabulary (per mutator type).

### 5.10 Done criteria

- Unconfigured workspaces unaffected.
- Configured workspaces run mutation testing end-to-end.
- Mutation results persist into gate-state model.
- Low-score findings are behavior-focused.
- `make test`, `make compile`, `make validate-catalog` all pass.

## 6. Wave H1 — Smell-to-Refactoring Guidance

### 6.1 Objective

Add a deterministic mapping layer that converts smell or static-analysis findings into
refactoring guidance for coding agents.

### 6.2 New files

- `extensions/itx-gates/hooks/smell_mapping.py`
- `presets/base/smell-catalog.yml` (data, not code)
- `presets/base/templates/smell-skill-template.md` (Claude Code `SKILL.md` scaffold, opt-in)

Edits:

- `orchestrator_brief.py._generate_execution_brief` — add a "Smell guidance" section, rendered
  only when smell-tagged findings exist.
- `scripts/validate_catalog.py` — validate `smell-catalog.yml` against a JSON Schema.
- `Makefile` — register new files.

### 6.3 Catalog schema (`presets/base/smell-catalog.yml`)

```yaml
version: 1
smells:
  - id: LONG_METHOD
    fowler_name: "Long Method"
    aliases: ["Long Function"]
    refactorings:
      - id: EXTRACT_FUNCTION
        intent: "Lift a coherent fragment into its own named function."
        url: https://refactoring.com/catalog/extractFunction.html
        priority: 1
      - id: REPLACE_TEMP_WITH_QUERY
        intent: "Turn a local temp into a reusable query method."
        url: https://refactoring.com/catalog/replaceTempWithQuery.html
        priority: 2
    detectors:
      sonar:      [java:S138, java:S3776]
      eslint:     [max-lines-per-function, complexity]
      pylint:     [R0915, R1260]
      pmd:        [ExcessiveMethodLength, CyclomaticComplexity]
      checkstyle: [MethodLength]
      radon:      ["cc --min C"]
    test_first:
      strategy: characterization
      hint: "Pin whole-function behavior with a golden-output test before extracting."
    advisory: >
      Prefer Extract Function. Preserve the outer signature. Name extractions
      after intent. Stop at 3 extractions or cyclomatic <= 5.
    language_overlays:
      java_8:
        prefer: [stream-collect]
        note: "Prefer Stream.collect over Stream.toList (Java 16+)."
      dotnet_fx_2:
        avoid: [LINQ, async_await]
        note: "No LINQ/async on .NET FX 2.0; explicit iteration + delegates."
```

### 6.4 Curated smell set at launch (5 entries)

`LONG_METHOD`, `FEATURE_ENVY`, `LARGE_CLASS`, `SHOTGUN_SURGERY`, `DATA_CLUMPS`. Each follows the
schema in §6.3; refactorings and detector IDs are seeded from
[refactoring.com/catalog](https://refactoring.com/catalog/) and the research synthesis mapping
table.

### 6.5 Reverse index for linter output

`smell_mapping.py` builds a reverse index at import time: `{linter_rule_id: smell_id}`. When a
finding carries a rule ID (from Wave F's generic adapter, or a future linter adapter), the mapper
looks up the canonical smell and appends the advisory block to `execution-brief.md`. Unknown
rule IDs are a no-op (guidance is advisory, never blocking).

### 6.6 Optional Agent Skill scaffold

`presets/base/templates/smell-skill-template.md` — a Claude Code-compatible `SKILL.md` frontmatter
scaffold (name, description, argument-hint, allowed-tools). Opt-in; workspaces that want
per-smell slash commands copy the template. Not required for the wave to pass.

### 6.7 Design rules

1. Mapping is additive guidance, never a mandatory hard gate.
2. Missing smell integration must not break the workspace.
3. Guidance is concise, remediation-focused, and advisory.
4. Unknown-smell input produces a pointer to `refactoring.com/catalog`, not a failure.

### 6.8 Tests

- Smell-to-guidance mapping lookup.
- Unknown-smell fallback.
- Reverse-index construction.
- Execution-brief enrichment when smell findings are present.
- No-op behavior when no smell source is configured.
- Catalog-schema validation inside `validate_catalog.py`.

### 6.9 Done criteria

- Curated smell mapping exists (5 entries).
- Guidance surfaces without mandatory external tool coupling.
- Tests exist for mapping, fallback, schema validation, and brief enrichment.

## 7. Wave H2 — Temporal Fakes Harness Capability

### 7.1 Objective

Provide an optional, language-agnostic scaffold under `harnesses/temporal-fakes/` for stateful
local fake services that model temporal evolution of real systems. Not a simulator platform.

### 7.2 Directory contents

```
harnesses/temporal-fakes/
  README.md                 Pattern definition, when/when-not, 4 fidelity patterns, usage
  scenarios.yaml            Example scenario registry (seed below)
  scenarios.schema.json     JSON Schema for the registry (validated via validate_catalog.py)
  example-fake/
    fake_deployment.py      ~100-line stateful deployment-state fake (HTTP)
    contract_test.py        Pact-less contract test skeleton (stubbed "real" block)
  process-compose.yaml      Optional orchestrator manifest
  adapters/
    mcp-adapter.md          How to wrap /scenarios/inject as MCP tools (~50 lines)
  ANTIPATTERNS.md           8 concrete anti-patterns from research
```

### 7.3 Chosen example — "fake deployment" state machine

State machine: `idle -> deploying -> healthy -> degraded -> failed`. Exercises transitions, a time
axis, and a fault-injection surface. HTTP API (language-neutral, curl-testable):

- `GET  /state` -> `{state, since_ms, metrics: {replicas_ready, error_rate}}`
- `POST /deploy` -> triggers `idle -> deploying -> healthy` over ~30s
- `POST /scenarios/inject` body `{id, type, params, duration_s}` -> e.g. degrade
- `POST /scenarios/clear`
- `GET  /scenarios` -> active injections + remaining time
- `GET  /healthz`

Single-process, 1s ticker. Clock injected via constructor so tests can fast-forward.

### 7.4 Scenario registry — seed content and schema

```yaml
version: 1
scenarios:
  - id: degrade-error-rate
    description: Degrade deployment to 30% error rate for 60s
    target: { fake: deployment, instance: default }
    fault:
      type: degrade
      params: { error_rate: 0.3 }
    schedule: { start_after: 5s, duration: 60s, ramp_up: 10s }
  - id: deployment-failure
    target: { fake: deployment, instance: default }
    fault: { type: fail, params: {} }
    schedule: { duration: 30s }
```

Schema fields: `id, target{fake,instance}, fault{type,params}, schedule{start_after,duration,ramp_up}`.
Cross-cuts WireMock / Chaos Mesh / AWS FIS / Toxiproxy conventions. No DSL.

### 7.5 Orchestration — process-compose, not docker-compose

`process-compose` (F1bonacc1, Go, single binary) is the right primitive: readiness probes
(`http_get`, `exec`), `depends_on` with `condition: process_healthy`, no Docker requirement.
Aligns with the Radar anecdote which named it. Example manifest:

```yaml
version: "0.5"
processes:
  fake-service:
    command: python -m example_fake.fake_deployment
    readiness_probe:
      http_get: { host: 127.0.0.1, port: 8080, path: /healthz }
  scenario-loader:
    command: python -m example_fake.load_scenarios scenarios.yaml
    depends_on:
      fake-service: { condition: process_healthy }
    availability: { exit_on_end: true }
```

### 7.6 MCP is optional and documented, not shipped

`adapters/mcp-adapter.md` shows how to expose `/scenarios/inject` as MCP tools in ~50 lines. No
MCP code is shipped in this wave. Honors the explicit non-goal that H2 does not couple to any
specific agent stack.

### 7.7 Fidelity patterns documented in README

Four patterns named explicitly, one paragraph each:

1. **Contract tests** (Fowler) — one suite, two runs (fake and real). Minimum requirement.
2. **Consumer-driven contracts** (Pact) — when the fake stands in for an owned service.
3. **Self-initializing fake / record-replay** (Fowler, VCR, nock) — bootstrap for first scenario.
4. **Shadow / dual-run testing** (Diffy, GoReplay, Istio mirroring) — strongest drift detector.

### 7.8 Anti-patterns (`ANTIPATTERNS.md`)

Codifies 8 failure modes:

- Drift without contract tests.
- Consumer-owned fakes (instead of provider-owned per Google SWE book Ch.13).
- Simulator creep (match the API contract, not internal details).
- Mocks disguised as fakes (no state, no time, no fidelity claim).
- Non-deterministic wall-clock time (inject clock; support virtual time).
- Unbounded scenario registry (treat `scenarios.yaml` as code).
- Fault injection without steady-state assertions (LitmusChaos "probes").
- Coupling the fake to HTTP (keep state machine as a library; HTTP is a thin adapter).

### 7.9 Design rules

1. Lightweight scaffold.
2. Optimized for reuse and adaptation.
3. Clear examples over heavy framework code.
4. Not a full simulator platform in this wave.

### 7.10 Tests / checks

- Harness files structurally valid.
- `scenarios.yaml` conforms to `scenarios.schema.json` (new check in `validate_catalog.py`).
- If `example-fake/fake_deployment.py` is shipped, a small unit test verifying state-machine
  transitions.
- Catalog validation stays green.

### 7.11 Done criteria

- `harnesses/temporal-fakes/` exists with the contents listed in §7.2.
- Documented.
- Optional: does not change core gate requirements.
- Repository validation remains green.

## 8. Commit structure

One branch `itx-tech-radar-program`, seven commits:

1. Wave F runtime + adapters + rule-to-pattern mapper + policy + tests.
2. Wave F docs (`polyglot_adapters.md`, ArchUnit helper example, sample config).
3. Wave G runtime + adapters (including `python_adapter.py`) + policy + tests.
4. Wave G docs + remediation vocabulary reference + sample config.
5. Wave H1 `smell_mapping.py` + `smell-catalog.yml` + schema validation + tests + brief
   integration.
6. Wave H2 harness scaffold (README, example fake, scenarios, process-compose manifest, schema,
   `mcp-adapter.md`, `ANTIPATTERNS.md`).
7. Final integration cleanup (Makefile compile list, release-script touch if new py files,
   documentation index updates). Only if narrow.

Validation triplet after every wave:

```bash
cd /Users/sprivalov/itexus/src/itx-spec-kit
make test
make compile
make validate-catalog
```

On any red: stop, fix the current wave, re-run the triplet, continue only after all three pass.

## 9. Backward compatibility rules

1. Existing workspaces without new config keep working.
2. Existing `itx-gates` lifecycle commands keep working.
3. Existing gate-state artifact structure remains readable.
4. New artifacts may be added; old consumers must not break when they are absent.
5. New capability defaults are non-breaking and opt-in.

## 10. Open decision

Workspace-overlay file location. Options:

- `.specify/config.yml` (recommended — matches the existing `.specify/context/` layout).
- `.specify/quality.yml` (narrower scope, but forks configuration across multiple files).
- Merge into an existing file (not recommended — no clear host file today).

### Resolution to the Open Decision
*   **The Verdict:** Go with **`.specify/config.yml`**. 
*   **Reasoning:** Introducing `.specify/quality.yml` fragments the developer configuration. Centralizing settings in `.specify/config.yml` creates a single source of truth for the workspace override, mapping cleanly to the `quality.*` namespace defined in your policy blocks.

## 11. Risks (research-informed)

1. **Initial-scan noise.** First runs surface hundreds of violations; baselining (§3.4) is the
   mitigation. Requires a one-time `gatectl ... --baseline-update`.
2. **Spectral misclassification.** Downstream teams will try to point it at source code. Docs
   must be explicit: API specs only.
3. **ArchUnit JVM dependency.** Applies only to JVM workspaces; flag at the top of docs.
4. **Pitest incremental setup cost.** `scmMutationCoverage` requires Maven SCM plugin. Opt-in.
5. **Flaky mutants inflating CI time.** `flaky_reruns: 2` doubles CI cost for surviving mutants.
   Configurable.
6. **Over-fidelity / simulator creep** in Wave H2. `ANTIPATTERNS.md` guards by text; consider a
   CODEOWNERS note on `harnesses/temporal-fakes/` to slow drift.
7. **SARIF version skew.** Pin 2.1.0 in the generic parser; reject 2.0 at ingest.
8. **Makefile compile drift.** Every new `.py` must be added to `compile`. Add a test that globs
   `extensions/itx-gates/hooks/**/*.py` and diffs against the Makefile list.
9. **LLM hallucination of patterns.** Mitigated by the deterministic mapper + finite catalog; the
   LLM never authors findings.
10. **Equivalent mutant noise.** `.specify/mutation-ignore.yml` + `flaky_reruns` mitigate;
    accept <10% residual noise (Code Defenders data).

## 12. Out of scope

1. Rewriting `itx-gates` to another runtime.
2. Replacing the lifecycle-hooks orchestration.
3. LLM as source of truth for architecture correctness.
4. Global mutation enforcement across every downstream project.
5. Full enterprise simulator platform under `harnesses/`.
6. Reworking brownfield / workstream semantics.
7. Reopening packaging decisions already settled by the extension model.
8. iSMELL-style LLM-driven refactoring orchestration (noted as reference, not shipped).
9. RefactoringMiner / JDeodorant as pre-refactor detectors.
10. Pact / CDC infrastructure (documented as recommendation only in Wave H2).
11. MCP scenario-injection code (documented only).
12. CI workflow under `.github/workflows/` (noted absent; not added by this program).

## 13. Final acceptance criteria

The program is complete when:

1. Wave F complete and validated.
2. Wave G complete and validated.
3. Wave H complete and validated.
4. The repository passes:
   ```bash
   make test
   make compile
   make validate-catalog
   ```
5. Existing unconfigured workspaces are not forced into new behavior.
6. New capability paths are documented well enough for a downstream adopter to opt in.
7. The branch remains reviewable and logically segmented by wave.

## 14. Execution checklist

```
Step 1.  git checkout -b itx-tech-radar-program
Step 2.  Implement Wave F only.
Step 3.  make test && make compile && make validate-catalog
Step 4.  Green -> commit Wave F. Not green -> fix and re-run.
Step 5.  Implement Wave G only.
Step 6.  make test && make compile && make validate-catalog
Step 7.  Green -> commit Wave G.
Step 8.  Implement Wave H only.
Step 9.  make test && make compile && make validate-catalog
Step 10. Green -> commit Wave H.
Step 11. Final integration cleanup only if narrow.
Step 12. Run the validation triplet one final time.
```

## 15. References

### Architecture drift

- [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- [Freezing Architecture Rules](https://deepwiki.com/TNG/ArchUnit/2.3.2-freezing-architecture-rules)
- [Spectral CLI](https://github.com/stoplightio/spectral/blob/develop/docs/guides/2-cli.md)
- [Spring Modulith Verification](https://docs.spring.io/spring-modulith/reference/verification.html)
- [iSMELL (ASE 2024)](https://dl.acm.org/doi/10.1145/3691620.3695508)
- [dependency-cruiser](https://github.com/sverweij/dependency-cruiser)
- [import-linter](https://import-linter.readthedocs.io/)
- [Deply](https://github.com/vashkatsi/deply)
- [PyTestArch](https://pypi.org/project/PyTestArch/)
- [depguard](https://github.com/OpenPeeDeeP/depguard)
- [Konsist](https://github.com/LemonAppDev/konsist)
- [SARIF v2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)

### Mutation testing

- [mutation-testing-report-schema](https://github.com/stryker-mutator/mutation-testing-elements)
- [StrykerJS incremental mode](https://stryker-mutator.io/docs/stryker-js/incremental/)
- [cargo-mutants](https://mutants.rs/)
- [Pitest incremental analysis](https://pitest.org/quickstart/incremental_analysis/)
- [Cosmic Ray](https://cosmic-ray.readthedocs.io/)
- [Facebook — What It Would Take to Use Mutation Testing in Industry (arXiv 2010.13464)](https://arxiv.org/pdf/2010.13464)
- [MutGen at Meta (arXiv 2501.12862)](https://arxiv.org/pdf/2501.12862)
- [Flaky Mutants — Shi et al.](https://mir.cs.illinois.edu/marinov/publications/ShiETAL19FlakyMutation.pdf)
- [Over-mocked AI tests (arXiv 2602.00409)](https://arxiv.org/html/2602.00409)
- [Sentry JS mutation testing](https://sentry.engineering/blog/js-mutation-testing-our-sdks)

### Smell mapping

- [Fowler Refactoring Catalog](https://refactoring.com/catalog/)
- [Refactoring.Guru — Smells](https://refactoring.guru/refactoring/smells)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Luzkan smell catalog](https://github.com/Luzkan/smells)
- [RefactoringMiner](https://github.com/tsantalis/RefactoringMiner)
- [JDeodorant](https://github.com/tsantalis/JDeodorant)
- [Sonar rule S138](https://rules.sonarsource.com/java/rspec-138/)
- [Characterization tests](https://en.wikipedia.org/wiki/Characterization_test)

### Temporal fakes

- [Thoughtworks Radar Vol. 34 PDF](https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2026/04/tr_technology_radar_vol_34_en.pdf)
- [Fowler — Test Double](https://martinfowler.com/bliki/TestDouble.html)
- [Fowler — Contract Test](https://martinfowler.com/bliki/ContractTest.html)
- [Fowler — Self-Initializing Fake](https://martinfowler.com/bliki/SelfInitializingFake.html)
- [SWE at Google Ch.13 — Test Doubles](https://abseil.io/resources/swe-book/html/ch13.html)
- [WireMock — Stateful Behaviour](https://wiremock.org/docs/stateful-behaviour/)
- [Toxiproxy](https://github.com/Shopify/toxiproxy)
- [LocalStack — Chaos API](https://docs.localstack.cloud/user-guide/chaos-engineering/chaos-api/)
- [AWS FIS experiment templates](https://docs.aws.amazon.com/fis/latest/userguide/experiment-template-example.html)
- [Chaos Mesh — PodChaos](https://chaos-mesh.org/docs/simulate-pod-chaos-on-kubernetes/)
- [process-compose](https://f1bonacc1.github.io/process-compose/)
- [Pact — Consumer-Driven Contracts](https://docs.pact.io/getting_started/comparisons)
