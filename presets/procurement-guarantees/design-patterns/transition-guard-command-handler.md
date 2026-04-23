---
tags:
  - command
  - handler
  - transition
  - state-machine
  - lifecycle
anti_tags:
  - react
  - ui
  - component
  - modal
  - css
  - html
phases:
  - after_plan
  - after_tasks
  - after_review
---

# Command Handler: Transition Guard

> **Domain:** Procurement Guarantees
> **Phase relevance:** Tasks, Implement
> **Extends:** `../../base/design-patterns/command-and-handler.md`

---

## 1. Intent

Represent each legal lifecycle action as an explicit **Command Handler** so
state changes, permissions, evidence creation, and downstream side effects stay
consistent.

Example commands:

- `SubmitApplication`
- `ApproveIssuance`
- `AmendUndertaking`
- `RegisterDemand`
- `AcceptRelease`

---

## 2. Structure

```python
class ApproveIssuanceHandler:
    def handle(self, cmd: ApproveIssuance) -> Result[TrackId, IssuanceError]:
        track = self._repo.load(cmd.track_id)
        track.assert_can_issue(...)
        track.issue(...)
        self._repo.save(track)
        self._events.publish(...)
        return Ok(track.id)
```

The handler owns:

- source-state validation
- authorization and guard invocation
- mutation of the aggregate
- evidence/history emission
- downstream events or adapter calls

---

## 3. Why It Helps

- prevents direct status mutation
- keeps transition semantics testable
- gives one home for side effects and history writes

---

## 4. AI Agent Directives

1. Use one handler per business transition, not one giant “update status” method.
2. Keep external callbacks downstream from the transition boundary.
3. Return typed business errors instead of silent no-ops or generic exceptions.
