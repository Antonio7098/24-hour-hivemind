# Mission Brief: Hivemind (CLI) - Deep Beta Program

## Overview
**Hivemind** is a **local-first, event-sourced CLI orchestration system** for agentic coding workflows.

This packet is for **human-style beta testers** who will run Hivemind like real developers shipping real software.

You are expected to:
- Build realistic projects and workflows in sandbox repos.
- Push normal and edge behaviors until something breaks.
- Report bugs, operator pain, and DX/docs failures with hard evidence.

**Explicit non-goal:** writing unit tests or integration tests for Hivemind internals.

**Primary goal:** validate production-like CLI behavior under realistic developer usage.

---

## Capability Surface (2026 refresh)

These commands are in scope and should be exercised deeply:

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

Supported output formats:
- `-f table` (default)
- `-f json`
- `-f yaml`

---

## What changed since the old packet

Testers must now assume these are first-class behaviors:

1. **Checkpoint gating is mandatory** for task completion in runtime flows.
2. **Verification workflow includes human authority controls** (`verify results`, `verify override`).
3. **Retry behavior is modeful** (`continue` vs `clean`) and must be validated with worktree evidence.
4. **Flow lifecycle controls** (`pause`, `resume`, `abort`) are operational and should be stress-tested.
5. **Merge protocol is explicit and multi-step** (`prepare -> approve -> execute`).
6. **Runtime projection events** (commands, tool calls, todo snapshots, narrative output) are part of observability expectations.

---

## Mental model for deep testing

Think in these layers:

- **Source of truth:** append-only events.
- **Derived state:** project/task/graph/flow state reconstructed from events.
- **Scheduler + runtime:** flow tick executes eligible tasks through adapter contracts.
- **Git boundaries:** worktrees isolate execution; merge integrates approved results.
- **Human controls:** checkpoints, overrides, pause/resume/abort are safety valves.

**Invariant:** If action/state is not evidenced in events + derived state, treat it as untrusted.

---

## Deep tester operating doctrine

### Roleplay rules
- Act as a professional engineer under delivery pressure.
- Use Hivemind to build real artifacts (services, CLIs, docs, data pipelines, frontend modules).
- Report from operator perspective: "Can I ship with this? What would break at 2am?"

### Not allowed
- No synthetic unit/integration test writing against Hivemind internals.
- No purely toy interaction with no production-like intent.

### Required behavior
- Start simple, then escalate complexity each run.
- Intentionally hit failure paths and recovery paths.
- Always capture minimal reproducible command sequences for suspected bugs.

---

## Environment and isolation requirements

- Hivemind source: `Hivemind/hivemind`
- Runner: `Hivemind/24-hour-hivemind`
- Runs folder: `Hivemind/24-hour-hivemind/runs`

For every run:
- Use run-local `HIVEMIND_DATA_DIR` (never `~/.hivemind`).
- Use run-local sandbox git repo(s).
- Capture all CLI output to artifacts in the run directory.

Recommended tooling:
- Rust toolchain (`cargo`, `rustc`)
- Git
- `jq`
- runtime adapter binary (recommended: OpenCode)

---

## Complexity ladder expected by checklist

Checklist items are intentionally staged:

1. **Smoke and contract sanity**
2. **Core CRUD + graph correctness**
3. **Flow/runtime/checkpoint reliability**
4. **Failure/recovery and operator controls**
5. **Merge safety, replay determinism, and event audits**
6. **Long-running production simulations**
7. **Industry roleplay scenarios** (fintech, health, ecommerce, devtools, infra)

Each item should go deep in one area and intentionally hunt edge-case bugs.

---

## Known high-risk themes to aggressively probe

- Active flow safety when repositories/runtime config change mid-flight.
- Checkpoint race/timing windows and invalid-state completion attempts.
- Retry mode correctness and worktree state preservation.
- Flow state transitions under pause/resume/abort in odd timing sequences.
- Merge correctness under divergence/conflicts/dirty trees.
- Event replay parity with observed state (`events replay --verify`).
- Exit code and structured error consistency for automation consumers.

---

## Reporting contract (mandatory)

Every checklist run must produce `{ITEM_ID}-FINAL-REPORT.md` in `runs/<timestamp-or-id>/`.

Include:
1. Exact commands run (copy/paste ready).
2. Environment snapshot:
   - OS
   - `hivemind --version`
   - `git --version`
   - `HIVEMIND_DATA_DIR`
   - runtime binary + version
3. Intended developer scenario (what product/problem you were simulating).
4. Expected vs actual behavior.
5. Event evidence (`events stream/list/inspect`), attempt/worktree evidence, and merge evidence where relevant.
6. Bug list with severity and minimal repro commands.
7. DX/docs recommendations.

Severity guide:
- **Critical:** data loss, false-success, replay mismatch, wrong merge result.
- **High:** core workflow blocked or stranded without safe recovery.
- **Medium:** recoverable but confusing/fragile behavior.
- **Low:** polish/documentation/help-text issues.

---

## References for testers

- `Hivemind/hivemind/README.md`
- `Hivemind/hivemind/docs/overview/quickstart.md`
- `Hivemind/hivemind/docs/design/cli-operational-semantics.md`
- `Hivemind/hivemind/ops/ROADMAP.md`
- `Hivemind/hivemind/ops/reports/`

### Documentation access expectations
- Navigate the documentation tree locally at `Hivemind/hivemind/docs/`. Treat it as the canonical source for CLI semantics, runtime adapters, and operational guarantees.
- `Hivemind/hivemind/docs/design/cli-operational-semantics.md` is the contract of record for command behavior; every inconsistency you find between reality and this document must be reported.
- When docs are silent, outdated, or contradictory, record the exact file + line references and describe the discrepancy in your final report.

### CLI discoverability expectations
- Systematically exercise `hivemind --help`, each top-level subcommand help (e.g., `hivemind flow --help`), and nested command help (e.g., `hivemind flow start --help`).
- Note any missing examples, ambiguous flag descriptions, or inconsistent formatting.
- Include a “CLI discovery report” section in your run report summarizing help-text gaps, misleading guidance, or opportunities for better onboarding.

---

## Final reminder

You are a beta tester simulating a real engineer, not a framework tester.
Treat every run as "Would I trust this for production delivery under pressure?"
