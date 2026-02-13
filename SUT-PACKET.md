# Mission Brief: Hivemind (CLI) - Deep Beta Program

## Overview
**Hivemind** is a **local-first, event-sourced CLI orchestration system** for agentic coding workflows.

This packet is for **human-style beta testers** who will run Hivemind like real developers shipping real software.

You are expected to:
- Build realistic projects and workflows in sandbox repos.
- Push normal and edge behaviors until something breaks.
- Report bugs, operator pain, and DX/docs failures with hard evidence.

**Explicit non-goal:** writing unit or integration tests for Hivemind internals.

**Primary goal:** validate production-like CLI behavior under realistic developer usage.

---

## Capability Surface (2026 refresh)

Test and stress these commands:
- `hivemind version`
- `hivemind project create|list|inspect|update|runtime-set|attach-repo|detach-repo`
- `hivemind task create|list|inspect|update|close|start|complete|retry|abort`
- `hivemind graph create|add-dependency|validate`
- `hivemind flow create|start|tick|pause|resume|abort|status`
- `hivemind events list|inspect|stream|replay`
- `hivemind verify run|results|override`
- `hivemind attempt inspect [--context] [--diff] [--output]`
- `hivemind checkpoint complete`
- `hivemind merge prepare|approve|execute`
- `hivemind worktree list|inspect|cleanup`

Supported formats: `-f table` (default), `-f json`, `-f yaml`.

---

## What changed since the old packet

1. **Checkpoint gating is mandatory** before task completion in runtime flows.
2. **Verification workflow includes human authority controls** (`verify results`, `verify override`).
3. **Retry behavior is modeful** (`continue` vs `clean`) and must be validated via worktree/marker evidence.
4. **Flow lifecycle controls** (`pause`, `resume`, `abort`) are operational and must be stress-tested.
5. **Merge protocol is explicit and multi-step** (`prepare → approve → execute`).
6. **Runtime projection events** (commands, tool calls, todo snapshots, narrative output) are part of observability expectations.

---

## Mental model for deep testing

- **Source of truth:** append-only events.
- **Derived state:** project/task/graph/flow/merge reconstructed from events.
- **Scheduler + runtime:** flow tick executes eligible tasks via adapters.
- **Git boundaries:** worktrees isolate execution; merge integrates approved results.
- **Human controls:** checkpoints, overrides, pause/resume/abort safeguard the flow.

**Invariant:** If it isn’t evidenced in events and derived state, assume it didn’t happen.

---

## Deep tester operating doctrine

### Roleplay rules
- Act as a professional engineer under delivery pressure.
- Build real artifacts (services, CLIs, docs, data pipelines, frontend modules).
- Report from the operator perspective: "Would I ship this? What breaks at 2am?"

### Not allowed
- No synthetic unit/integration tests against Hivemind internals.
- No purely toy interactions without production intent.

### Required behavior
- Start simple, escalate complexity each run.
- Intentionally hit failure and recovery paths.
- Capture minimal reproducible command sequences for every suspected bug.

---

## Environment and isolation requirements

- Source repo: `Hivemind/hivemind`
- Runner: `Hivemind/24-hour-hivemind`
- Runs folder: `Hivemind/24-hour-hivemind/runs`

For every run:
- Use run-local `HIVEMIND_DATA_DIR` (never `~/.hivemind`).
- Use run-local sandbox git repo(s) under `{{RUN_DIR}}`.
- Capture all CLI output/logs inside the run directory.

Recommended tooling: Rust toolchain (`cargo`, `rustc`), Git, `jq`, runtime adapter binary (OpenCode recommended).

---

## Complexity ladder for checklist items

1. **Smoke / contract sanity**
2. **Core CRUD + graph correctness**
3. **Flow / runtime / checkpoint reliability**
4. **Failure, recovery, operator controls**
5. **Merge safety, replay determinism, event audits**
6. **Long-running production simulations**
7. **Industry roleplay scenarios** (fintech, healthcare, ecommerce, devtools, infra)

Each checklist item should dig deeply into one area and hunt for edge-case bugs.

---

## Known high-risk themes

- Active flow safety when repos/runtime config change mid-flight.
- Checkpoint race/timing windows and invalid completion attempts.
- Retry mode correctness and worktree preservation.
- Flow state transitions under rapid pause/resume/abort sequences.
- Merge correctness with divergence/conflicts/dirty trees.
- Event replay parity with observed state (`events replay --verify`).
- Exit-code + structured-error consistency for automation consumers.

---

## Reporting contract

Every checklist run must produce `{ITEM_ID}-FINAL-REPORT.md` in `{{RUN_DIR}}`.

### Include
1. Exact commands (copy/paste ready).
2. Environment snapshot:
   - OS
   - `hivemind --version`
   - `git --version`
   - `HIVEMIND_DATA_DIR`
   - runtime binary + version
3. Developer scenario roleplay description.
4. Expected vs actual behavior.
5. Evidence: `events stream/list/inspect`, `attempt inspect --diff/--output`, worktree paths, merge artifacts.
6. Bug list with severity and minimal repro steps.
7. DX/docs recommendations.
8. CLI discovery notes (see below).

### Severity guide
- **Critical:** data loss, false-success, replay mismatch, incorrect merge result.
- **High:** core workflow blocked/stranded without safe recovery.
- **Medium:** recoverable but confusing/fragile behavior.
- **Low:** polish, documentation, help-text issues.

---

## References for testers

- `Hivemind/hivemind/README.md`
- `Hivemind/hivemind/docs/overview/quickstart.md`
- `Hivemind/hivemind/docs/design/cli-operational-semantics.md`
- `Hivemind/hivemind/docs/overview/principles.md`
- `Hivemind/hivemind/ops/ROADMAP.md`
- `Hivemind/hivemind/ops/reports/`

### Documentation access expectations
- Navigate `Hivemind/hivemind/docs/` locally; treat it as the canonical source for CLI semantics, runtime adapters, operational guarantees, and product principles.
- `docs/design/cli-operational-semantics.md` is the contract of record for commands; report any discrepancies.
- `docs/overview/principles.md` defines the reliability/safety ethos; highlight any behavior that conflicts with these principles.
- When docs are silent/outdated/contradictory, cite file + line numbers and describe the discrepancy in the final report.

### CLI discoverability expectations
- Systematically exercise `hivemind --help`, each top-level subcommand help, and nested command help.
- Note missing examples, ambiguous flag descriptions, inconsistent formatting, or mismatched defaults.
- Include a "CLI discovery report" section summarizing help-text gaps, misleading guidance, or onboarding improvements.

---

## Final reminder

You are a beta tester simulating a real engineer. Treat every run as: "Would I trust this for production delivery under pressure?"
