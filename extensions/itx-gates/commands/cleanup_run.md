---
description: "Run the Spec-Kit cleanup extension via the universal runner adapter"
---

## Purpose

Execute `/speckit.cleanup.run` by delegating to the installed `spec-kit-cleanup`
community extension through the universal runner adapter. The adapter tries the
Spec-Kit CLI first (`spec-kit` → `specify` → `uvx`). If no CLI can dispatch
the command, the adapter **resolves the extension prompt locally** from the
workspace's `.specify/extensions/` registry and prints it between
`---SPECKIT-PROMPT---` / `---END-SPECKIT-PROMPT---` markers for the calling
agent to execute.

## How to execute

```bash
python .specify/extensions/itx-gates/commands/run_speckit.py \
  --command cleanup.run \
  --workspace .
```

To force a specific CLI backend, pass `--cli`:

```bash
python .specify/extensions/itx-gates/commands/run_speckit.py \
  --command cleanup.run \
  --cli uvx \
  --workspace .
```

This delegates to `dsrednicki/spec-kit-cleanup`. The community extension
defines what cleanup tasks to run and how results are reported.

The adapter automatically probes `specify` before using it; if the installed
`specify` does not support extension commands it is skipped. If no CLI can
dispatch the command, local resolution reads the extension prompt from the
workspace so the command works without any CLI installed.
