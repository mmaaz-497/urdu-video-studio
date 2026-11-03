---
id: 0004
title: Dependency ordered tasks for video generation
stage: tasks
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: /sp.tasks
labels: ["tasks", "video-generation", "csrf", "storage-provider", "runpod-volume"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/tasks.md
tests:
 - none (task list only; no code written)
---

## Prompt

Generate tasks.md for specs/001-video-generation with these rules:

Ordering:
- Phase 1 Setup and Phase 2 Foundation first (repo skeleton, docker-compose.dev.yml, config/.env.example, DB models + Alembic, error-handling + logging with request/job IDs, session auth core).
- Then user stories in priority order (P1 Create → P2 My Videos → P3 Password reset → P4 Landing page). Each story must be independently runnable and demoable at its checkpoint.
- Build P1 end-to-end in VIDEO_PROVIDER=mock mode FIRST (full flow works with zero GPU cost). Put the real gpu-worker (ComfyUI + Wan 2.2 + OmniVoice handler) and the RunPod provider in a separate later phase.
- Final phase: production deploy (docker-compose.prod.yml, Caddyfile, README).

Add these items that the plan missed:
1. STORAGE_PROVIDER setting: "local" (files saved on disk and served by the backend, for development) or "r2" (production). Same interface as the R2 storage service.
2. CSRF protection for the cookie session: SameSite=Lax cookie plus a CSRF token check on all state-changing requests.
3. GPU worker reads model weights from a RunPod network volume (not baked into the image); document the volume layout and a one-time download script for the weights.

Task style:
- Small tasks (one clear outcome each, ~1 file or tightly related files), each with exact file paths and the FR it satisfies.
- Mark parallelizable tasks [P].
- Tests ONLY for the three critical paths in the constitution (auth incl. password reset, video job state machine, LLM output parsing) — no other tests.
- Every task that calls an external service must mention its timeout/retry/friendly-error handling.

## Response snapshot

Ran `check-prerequisites.sh`, re-read spec.md/plan.md/data-model.md/research.md/contracts/openapi.yaml/quickstart.md/design-system.md in full, then wrote `specs/001-video-generation/tasks.md` with 95 tasks (T001–T095) across 8 phases matching the exact ordering requested:

- **Phase 1 Setup (T001–T008)**: monorepo skeleton, backend/frontend project init, docker-compose.dev.yml (Postgres+Redis only), `.env.example` files (including the two new settings), lint config.
- **Phase 2 Foundational (T009–T037)**: config, DB engine+4 models+Alembic migration, structured logging + AppError/request-id handling, argon2 hashing, Redis session store, **CSRF double-submit middleware (new item #2)**, `usage_service.py` (atomic row-locked limit helpers), **`StorageService` protocol + `local`/`r2` implementations (new item #1)**, FastAPI app bootstrap, register/login/logout/`GET /me`, `test_auth.py` (critical path #1, base coverage), frontend api-client/theme-provider/root-layout/login/register pages, auth route guard middleware.
- **Phase 3 US1 (T038–T060, mock mode only)**: moderation + LLM structured-output service with scene/word-count server-side re-validation and retry-once, `/scripts` and `/voices` endpoints, idempotent row-locked `video_job_service`, mock asset bundle + FFmpeg assembly (atempo≤10%-then-fail per FR-017), RQ worker, stale-job sweeper, `test_video_job_state_machine.py` and `test_llm_output_parsing.py` (critical paths #2/#3), Create/Review/Progress frontend pages with option cards, word counter, and progress stepper.
- **Phase 4 US2 (T061–T065)**: list/delete/retry extensions to `video_job_service`/`videos.py`, usage badge ("X of Y left today"), My Videos grid.
- **Phase 5 US3 (T066–T072)**: Resend email service, password-reset token service, forgot/reset-password endpoints, `test_auth.py` extended with reset-token lifecycle coverage, forgot/reset-password pages.
- **Phase 6 US4 (T073–T081)**: theme toggle + site header, hero/how-it-works/showcase/FAQ/footer marketing components, landing page assembly, sample video assets.
- **Phase 7 Real GPU Pipeline (T082–T090, separate later phase as instructed)**: **RunPod network-volume layout doc + one-time weight-download script (new item #3)**, parameterized ComfyUI Wan 2.2 workflow, RunPod handler with per-scene progress reporting, OmniVoice single-pass synthesis, presigned-URL upload from the GPU worker, Dockerfile that does NOT bake in weights, backend `runpod_provider.py`, and `video_pipeline.py` extended to branch on `VIDEO_PROVIDER`.
- **Phase 8 Production Deployment (T091–T095, final phase)**: backend/frontend Dockerfiles, `docker-compose.prod.yml`, Caddyfile, root `README.md` with the CC-BY-NC licensing notice.

Every task names exact file path(s) and its satisfied FR(s); every task touching an external service (OpenAI moderation/Agents SDK, Resend, R2, RunPod, `ffmpeg`, Redis, Postgres) states its timeout/retry/friendly-error behavior inline, per Constitution Principle V. Tests are limited to exactly the 3 constitution-mandated critical paths (T031/T070 combined = auth incl. password reset, T052 state machine, T053 LLM parsing) — no other test tasks were generated. Added a Dependencies & Execution Order section explaining story independence (US2 extends US1's files but US1 doesn't need US2; US3 and US4 are fully independent and parallelizable with US1), a parallel-example block, and a 3-strategy Implementation Strategy section (MVP-first, incremental delivery, parallel team staffing).

## Outcome

- ✅ Impact: Feature 001-video-generation has a complete, dependency-ordered, immediately-executable task list; ready for implementation to begin (starting with Phase 1).
- 🧪 Tests: none run (task-generation stage); the 3 critical-path test files are scheduled as T031/T070, T052, T053 within the task list itself.
- 📁 Files: `specs/001-video-generation/tasks.md` (created, 95 tasks)
- 🔁 Next prompts: Begin implementation at Phase 1 (Setup), or `/sp.analyze` first for a cross-artifact consistency check across spec/plan/tasks before writing code.
- 🧠 Reflection: The main structural decision was splitting `video_job_service.py`, `videos.py`, and `test_auth.py` across phases ("create in Foundational/US1, extend in US2/US3") rather than forcing every file to be born complete in one phase — this matches how the entities (VideoJob, Student auth) genuinely span multiple user stories per data-model.md, while still keeping each individual task small and single-outcome. The three "missed" items were each slotted into the phase where they're actually load-bearing rather than bolted on at the end: CSRF went into Foundational (applies to every state-changing request from day one), STORAGE_PROVIDER went into Foundational (US1's video pipeline needs it immediately), and the RunPod network volume went into Phase 7 (irrelevant until real GPU generation exists).

## Evaluation notes (flywheel)

- Failure modes observed: none — single-pass generation; re-read all six upstream design docs before drafting to avoid inventing file paths or FR references not already established.
- Graders run and results (PASS/FAIL): manual FR-coverage sweep (all 34 FRs from spec.md traced to at least one task) — PASS; checklist-format validation (every line matches `- [ ] T### [P?] [Story?] Description + file path`) — PASS; external-call timeout/retry mention sweep (moderation, LLM, storage_r2, sessions/Redis, db, ffmpeg, email, runpod, GPU→R2 PUT) — PASS, all 9 present.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
