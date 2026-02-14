# Mission Checklist: Hivemind (CLI) - Deep Beta Reset

> **How this checklist works**
>
> - **Do not change table columns.** Parser expects exactly: `ID | Target | Priority | Risk | Status`.
> - Allowed status values:
>   - `☐ Not Started`
>   - `✅ Completed`
>   - `❌ Failed`
> - Each row is one deep beta run and must produce `{ID}-FINAL-REPORT.md`.
> - These are **developer-roleplay scenarios**, not unit/integration tests.

## Tier 0: Baseline setup and trust in tooling (simple)
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| SMK-001 | Build `hivemind` with run-local state/target dirs; verify `hivemind version` and binary path correctness | P0 | High | ✅ Completed |
| SMK-002 | Help discoverability audit: `hivemind --help` + every top-level subcommand help for clarity and consistency | P0 | High | ✅ Completed |
| SMK-003 | Output contract: verify `-f table|json|yaml` shape/parsability for `project list`, `flow status`, `events list` | ✅ Completed | High | ✅ Completed |
| SMK-004 | Data isolation: prove no leakage between runs by rotating `HIVEMIND_DATA_DIR` and checking state separation | P0 | High | ✅ Completed |
| SMK-005 | Broken-pipe and shell ergonomics: pipe outputs through `head`, `grep`, `jq`; confirm no panic and sane exit behavior | P1 | Medium | ✅ Completed |

## Tier 1: Project and repository contract hardening
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| PRJ-001 | Create/update/inspect/list project lifecycle with restarts between operations to validate persistence | P0 | High | ✅ Completed |
| PRJ-002 | Attach valid repo then re-attach edge cases (duplicate name/path); verify deterministic conflict behavior | P0 | High | ✅ Completed |
| PRJ-003 | Attach invalid path and non-git path; verify structured category/code/origin plus recovery hints | P0 | High | ✅ Completed |
| PRJ-004 | Runtime-set matrix: valid config, invalid binary path, malformed env args; verify storage + error contracts | P0 | High | ✅ Completed |
| PRJ-005 | Active-flow repo lifecycle stress: attempt detach/update runtime while flow runs; validate safety rails and outcomes | P0 | High | ✅ Completed |

## Tier 2: Task and graph planning semantics
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| TSK-001 | Task CRUD with realistic descriptions/scopes and explicit acceptance criteria; validate inspect/list fidelity | P0 | High | ✅ Completed |
| TSK-002 | State-machine guardrails: close/start/complete/abort in invalid states; verify conflict handling and no silent mutation | P0 | High | ✅ Completed |
| TSK-003 | Graph creation from multi-task backlog; validate dependency direction semantics with non-trivial DAG | P0 | High | ✅ Completed |
| TSK-004 | Graph cycle and duplicate-edge probes; validate deterministic errors and idempotence behavior | P0 | High | ✅ Completed |
| TSK-005 | Graph immutability after flow creation; ensure post-lock mutations are rejected with clear guidance | P0 | High | ✅ Completed |

## Tier 3: Flow scheduler and checkpoint mechanics
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| FLW-001 | Flow start/readiness correctness across DAG branches (ready vs blocked transitions) | P0 | High | ✅ Completed |
| FLW-002 | Tick loop deep dive: run until terminal state while inspecting status after each tick for consistency | P0 | High | ✅ Completed |
| FLW-003 | Checkpoint enforcement path: reproduce incomplete checkpoint block and recover with proper `checkpoint complete` | P0 | High | ✅ Completed |
| FLW-004 | Checkpoint race probing: rapid tick/complete sequences to expose timing/state edge cases | P1 | Medium | ❌ Failed |
| FLW-005 | Pause/resume/abort stress test with odd sequencing and invalid-state attempts; verify event/state parity | P0 | High | ❌ Failed |

## Tier 4: Runtime adapter behavior and projection signals
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| RUN-001 | Real OpenCode path (`opencode/big-pickle`) from task start to completion in production-like prompt | P0 | High | ❌ Failed |
| RUN-002 | Runtime failure matrix: missing binary, timeout, non-zero exit, malformed output; verify clean failure boundaries | P0 | High | ☐ Not Started |
| RUN-003 | Runtime output attribution: validate `attempt inspect --output` and correlated event timelines | P0 | High | ☐ Not Started |
| RUN-004 | Projection event deep dive: force command/tool/todo/narrative emissions and verify event quality | P1 | Medium | ☐ Not Started |
| RUN-005 | Interactive gap characterization: attempt to trigger `runtime_input_provided` / `runtime_interrupted` and document limits | P1 | Medium | ☐ Not Started |

## Tier 5: Verification, overrides, and retries
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| VRF-001 | Required-check failure path with `verify results`; ensure failure data is actionable | P0 | High | ☐ Not Started |
| VRF-002 | Human override pass path: move verifying task to success and confirm downstream behavior | P0 | High | ☐ Not Started |
| VRF-003 | Human override fail path: keep flow blocked/failed appropriately and verify causality in events | P0 | High | ☐ Not Started |
| VRF-004 | Retry mode correctness: compare `task retry --mode continue` vs `--mode clean` with explicit marker evidence | P0 | High | ☐ Not Started |
| VRF-005 | Retry exhaustion and reset behavior under repeated failures; verify limits and operator ergonomics | P1 | Medium | ☐ Not Started |

## Tier 6: Worktrees, attempts, diffs, and scope safety
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| ART-001 | Baseline/diff integrity: validate attempt baselines and unified diffs against real file edits | P0 | High | ☐ Not Started |
| ART-002 | Worktree inspection correctness (`list`/`inspect`) across multiple tasks and attempts | P0 | High | ☐ Not Started |
| ART-003 | Scope-violation adversarial test: write outside scope and confirm block + preserved forensic state | P0 | High | ☐ Not Started |
| ART-004 | Failure preservation: ensure failed attempts preserve worktree and evidence for postmortem | P0 | High | ☐ Not Started |
| ART-005 | Cleanup safety/idempotence: `worktree cleanup` repeated execution and impact on recoverability | P1 | Medium | ☐ Not Started |

## Tier 7: Merge protocol and branch integrity
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| MRG-001 | Preconditions and gating: verify prepare blocked until flow completion and checks satisfied | P0 | High | ☐ Not Started |
| MRG-002 | Happy path merge with explicit prepare/approve/execute and target-branch verification | P0 | High | ☐ Not Started |
| MRG-003 | Conflict path: induce target-branch divergence and validate conflict surfacing quality | P0 | High | ☐ Not Started |
| MRG-004 | Idempotence and replayability: duplicate approve/execute calls and expected safe behavior | P1 | Medium | ☐ Not Started |
| MRG-005 | Dirty-repo safety: attempt merge with unrelated workspace changes and verify guardrails | P0 | High | ☐ Not Started |

## Tier 8: Events, replay, and deterministic operations
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| EVT-001 | Event filter correctness across `--project/--graph/--flow/--task` for noisy multi-flow runs | P0 | High | ☐ Not Started |
| EVT-002 | Event inspect/list not-found and malformed-id behavior with strict JSON contracts | P1 | Medium | ☐ Not Started |
| EVT-003 | Replay verification after complex run (`events replay --verify`); treat mismatch as critical | P0 | High | ☐ Not Started |
| EVT-004 | Correlation quality audit: ensure event metadata is sufficient for root-cause analysis | P0 | High | ☐ Not Started |
| EVT-005 | Exit-code contract sweep for user/conflict/system/runtime failures in machine-consumed flows | P0 | High | ☐ Not Started |

## Tier 9: Long-session reliability and operator recovery
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| REL-001 | 12+ task long-running project with retries, pauses, and restarts; verify no state drift | P0 | High | ☐ Not Started |
| REL-002 | Session interruption drill: kill terminal mid-run and recover purely via CLI observability commands | P0 | High | ☐ Not Started |
| REL-003 | Mid-flight mutation chaos: change project runtime/repo settings during active operations; document safety outcomes | P0 | High | ☐ Not Started |
| REL-004 | Large-event-volume responsiveness test (`events list`, `project list`, `flow status`) | P1 | Medium | ☐ Not Started |
| REL-005 | Comprehensive DX pain audit from an operator on-call perspective | P1 | Medium | ☐ Not Started |

## Tier 10: Industry roleplay scenarios (complex, production-grade)
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| IND-001 | **Fintech roleplay:** build transaction-ledger service changes with strict audit trail, verification gates, and cautious merge strategy | P0 | High | ☐ Not Started |
| IND-002 | **Healthcare roleplay:** implement patient-data workflow updates emphasizing scope boundaries and traceability under compliance constraints | P0 | High | ☐ Not Started |
| IND-003 | **Ecommerce roleplay:** ship checkout + inventory fixes under release pressure with hotfix branching and conflict handling | P0 | High | ☐ Not Started |
| IND-004 | **DevTools roleplay:** evolve a CI orchestration CLI with many interdependent tasks and heavy retry/override usage | P1 | Medium | ☐ Not Started |
| IND-005 | **Infra/SRE roleplay:** implement incident automation changes while simulating partial outages and recovery operations | P1 | Medium | ☐ Not Started |

## Tier 11: Final synthesis runs
| ID | Target | Priority | Risk | Status |
|----|--------|----------|------|--------|
| SYN-001 | Cross-tier regression sweep: rerun top 10 highest-risk findings for reproducibility and false-positive elimination | P0 | High | ☐ Not Started |
| SYN-002 | Production-readiness verdict: compile stop-ship issues, must-fix DX items, and confidence score with evidence links | P0 | High | ☐ Not Started |
