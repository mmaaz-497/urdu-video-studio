---
id: 0020
title: Scheduler lazy import, caps, restart check
stage: green
date: 2026-11-12
surface: agent
model: claude-opus-5-5
feature: 001-video-generation
branch: main
user: Maaz
command: (free-form) pre-first-deploy adjustments
labels: ["deployment","memory","scheduler","podman","phase-8"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - backend/app/services/video_job_service.py
 - infra/docker-compose.prod.yml
 - infra/release.sh
 - specs/001-video-generation/plan.md
 - specs/001-video-generation/tasks.md
 - README.md
tests:
 - backend pytest full suite (49 passed)
 - scheduler sweep measurement in prod compose (3 stale jobs swept, quota refunded; peak 60 MB)
 - 15 s mock job at worker cap 624m (ready; anon peak 364 MB) and scheduler cap 80m (peak 59 MB, no OOM)
 - check_restart_policies against docker shims: pass, wrong policy -> exit 1, missing container -> exit 1
 - shellcheck -S warning on infra scripts (pass)
---

## Prompt

Before the first deploy:
1. Apply the one-line fix so the scheduler no longer imports the OpenAI library, then re-measure the scheduler's real peak and set its cap to that + ~30%.
2. Give the freed memory to the worker: raise its cap to about 640 MB so a 15-second job has real headroom over the 420 MB peak. Keep the total at or under ~1.25 GB.
3. Add a post-deploy check to deploy.sh that confirms every uvs-* container has restart policy "always" (so podman-restart.service will bring it back after a reboot) — we will not reboot the live server just to test this.
Commit nothing; tell me when done.

## Response snapshot

Moved `from app.services import llm_service` inside `video_job_service.create_job` (scheduler no longer loads agents/openai; import RSS 142 -> 72 MB). Measured scheduler peak 60 MB while sweeping 3 stale jobs -> cap 80m. Worker raised to 624m (640m would have made the total 1296 MB; 624 keeps it at exactly 1280 MB = 1.25 GiB without shrinking postgres/backend). Added check_restart_policies to release.sh `check` (runs after every deploy, rollback and `deploy.sh check`): all six expected uvs-* containers must exist, every uvs-* container must have policy "always", podman-restart.service must be enabled. Docs updated. Nothing committed.

## Outcome

- ✅ Impact: worker headroom 48% over measured peak; scheduler 64 MB smaller; reboot safety asserted on every deploy without rebooting.
- 🧪 Tests: 49 passed; e2e job at new caps; check's pass/fail paths exercised.
- 📁 Files: 1 backend file, compose, release.sh, plan/tasks/README.
- 🔁 Next prompts: continue README Deploy step 1 on the real VPS.
- 🧠 Reflection: the lazy import also lowered the worker's job-process peak (420 -> 364 MB), since the RQ work-horse no longer loads the Agents SDK either.

## Evaluation notes (flywheel)

- Failure modes observed: test MAX_PROCESSING_SECONDS=20 let the sweeper fail a running job, which the worker then set to ready with failure_reason still set (pre-existing race, only reachable past MAX_PROCESSING_SECONDS; not changed).
- Graders run and results (PASS/FAIL): pytest PASS; ruff PASS; shellcheck PASS.
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): clear failure_reason / refuse failed->ready transition in the worker's final status update.
