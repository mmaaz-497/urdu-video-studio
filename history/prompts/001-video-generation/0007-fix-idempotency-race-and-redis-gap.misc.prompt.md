---
id: 0007
title: Fix idempotency race and redis gap
stage: misc
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: continue the work
labels: ["remediation", "idempotency", "redis", "tasks-md"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/tasks.md (edited: T020a added, T020/T041/T053/T056/T058 updated)
 - specs/001-video-generation/contracts/openapi.yaml (edited: 425 REQUEST_IN_PROGRESS response + updated idempotency description on POST /scripts)
tests:
 - none (planning-artifact edits only; T053's description was updated to add the new concurrent-claim test case, not executed)
---

## Prompt

continue the work

(Follow-up to the prior `/sp.analyze` re-run, whose report ended by asking:
"Would you like me to apply remediation edits for U1 (atomic Redis claim
pattern), G1 (shared Redis client task + T041 dependency), and A1 (clarify
key-generation timing in T056/T058)?" — interpreted as approval to proceed,
consistent with this session's auto-mode bias toward continuing rather than
re-asking.)

## Response snapshot

Applied all three remediations surfaced by the re-analysis:

- **U1**: Rewrote T041 to atomically claim the idempotency key via Redis
  `SETNX` (`"pending"`, 20s TTL) *before* any work starts, instead of
  check-then-act. A concurrent duplicate now gets 425 `REQUEST_IN_PROGRESS`
  immediately; a post-completion replay still returns the cached result;
  failure path `DEL`s the key so a legitimate retry isn't stuck behind a dead
  claim. Mirrored this into `contracts/openapi.yaml` (new 425 response +
  updated idempotency description on `POST /scripts`) and into T053's test
  description (added the concurrent-claim case alongside the existing
  post-completion replay case).
- **G1**: Added new foundational task **T020a**
  (`backend/app/core/redis_client.py`) — a shared `get_redis()` factory that
  both T020 (sessions) and T041 (script idempotency) now explicitly depend
  on, closing the "Redis client assumed but never established" gap.
- **A1**: Reworded T056 and T058 to state precisely when the idempotency key
  is generated — synchronously, in the same tick that disables the button,
  before any `await` — and that it's reused only for automatic retries of
  the same logical attempt, never regenerated per raw click event.

Verified after editing: task-ID/dependency graph integrity (102 tasks total,
zero dangling `depends on` references), all 34 FRs still individually
citable, and the OpenAPI contract's new 425 response matches T041's
description.

## Outcome

- ✅ Impact: Closes all 3 findings from the second `/sp.analyze` pass; the
  `/scripts` double-click/race design is now internally consistent across
  `tasks.md` and `contracts/openapi.yaml` before any code is written.
- 🧪 Tests: None executed (tasks.md/openapi.yaml are planning artifacts);
  T053's planned test description now explicitly covers both the
  post-completion-replay and concurrent-in-flight-claim cases.
- 📁 Files: `specs/001-video-generation/tasks.md`,
  `specs/001-video-generation/contracts/openapi.yaml`.
- 🔁 Next prompts: A third `/sp.analyze` pass would be the natural next check
  before `/sp.implement`, though diminishing returns are likely at this
  point; otherwise proceed straight to `/sp.implement` starting with Phase 1
  (Setup) → Phase 2 (Foundational, now including T020a).
- 🧠 Reflection: Treating "continue the work" as approval for a
  previously-offered, already-scoped remediation (rather than re-asking) kept
  momentum without taking on real risk — this was a docs/spec edit, fully
  reversible, and the user had already seen the exact 3 proposed changes in
  the prior report.

## Evaluation notes (flywheel)

- Failure modes observed: None new. The two-pass analyze→fix→analyze→fix
  cycle on this feature caught a real race condition (U1) that a single
  analyze pass missed, confirming the value of re-running `/sp.analyze`
  after any batch of remediation edits rather than treating one clean pass
  as final.
- Graders run and results (PASS/FAIL): N/A (no automated grader in this
  workflow).
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Consider making "re-run
  `/sp.analyze` once after applying remediations" a default step in this
  project's `/sp.analyze` command template, rather than something the
  assistant has to decide to do proactively.
