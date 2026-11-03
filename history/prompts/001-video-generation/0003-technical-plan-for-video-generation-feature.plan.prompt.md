---
id: 0003
title: Technical plan for video generation feature
stage: plan
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: /sp.plan
labels: ["plan", "video-generation", "architecture", "openapi", "design-system"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/plan.md
 - specs/001-video-generation/research.md
 - specs/001-video-generation/data-model.md
 - specs/001-video-generation/contracts/openapi.yaml
 - specs/001-video-generation/quickstart.md
 - specs/001-video-generation/design-system.md
 - CLAUDE.md
tests:
 - none (planning artifacts only; no application code written per instruction)
---

## Prompt

Plan specs/001-video-generation using the fixed stack in the constitution. Decisions and constraints:

## Repository layout (monorepo)
- frontend/  — Next.js App Router + TypeScript + Tailwind + shadcn/ui
- backend/   — FastAPI app + RQ worker (same codebase, separate entrypoints), SQLAlchemy 2 + Alembic
- gpu-worker/ — RunPod Serverless handler (Python): ComfyUI headless running the official Wan 2.2 TI2V-5B workflow (API-format JSON) + OmniVoice Urdu fine-tune (mlwithabdullah/omnivoice-urdu-6000) with two preset reference voices (male, female)
- infra/     — docker-compose.dev.yml (PostgreSQL + Redis only), docker-compose.prod.yml (frontend, backend, worker, postgres, redis), Caddyfile

## Video pipeline
- Backend creates the job after approval (idempotency key from the client prevents duplicate jobs on double-click; usage counter checked and incremented inside one DB transaction with row lock).
- RQ worker submits ONE RunPod job per video: inputs = scene prompts (1–3), aspect ratio (16:9 → 1280x704, 9:16 → 704x1280, 121 frames @24fps per clip), narration text, voice id, and presigned R2 PUT URLs. The GPU worker generates clips sequentially, synthesizes the voice, uploads raw clips + audio via the presigned URLs, and reports per-scene progress with RunPod progress updates. (Uploading via presigned URLs is the only storage write on GPU — justify it in Complexity Tracking; it avoids huge base64 payloads.)
- RQ worker polls RunPod status, maps progress to job steps in the DB, then runs FFmpeg on the server: normalize clips, concat, attach voice (atempo up to 1.10 if needed, otherwise fail per spec), hard-cap to the chosen duration, generate a thumbnail, upload final MP4 + thumbnail to R2, mark Ready.
- A periodic stale-job sweeper marks jobs Failed after a max processing time (configurable).
- VIDEO_PROVIDER=mock skips RunPod and uses bundled sample clips + a sample voice file so the full flow works locally for free.

## LLM step
- OpenAI Agents SDK agent with Pydantic structured output: corrected_idea, urdu_script, scenes[] (English prompts, count = duration/5), title. Model name from env (OPENAI_MODEL), small/cheap by default.
- Run the OpenAI moderation endpoint on the idea first; reject unsafe input per spec.
- Validate the output (scene count, script word limit for the duration); retry once on invalid output, then show a friendly error.

## Auth & email
- FastAPI-managed auth: email + password, argon2 hashing, session via httpOnly secure cookie (JWT or server session — choose and justify).
- Password reset: time-limited single-use token (hashed in DB), sent through a transactional email provider over SMTP/API configured in .env (provider-agnostic interface). Choose one with a free tier and document it.

## Frontend
- Status updates by polling the backend every 3s (TanStack Query); no websockets needed.
- next-themes for light/dark (default system), react-hook-form + zod for forms, Urdu text rendered RTL with "Noto Nastaliq Urdu" via next/font.

## UI design research (do this in research.md before designing screens)
- Research the landing pages and create/generate workspaces of leading AI video tools (Runway, Pika, Kling, Hailuo/MiniMax, Luma Dream Machine, Higgsfield). Note: hero patterns, prompt workspace layout, option cards (aspect ratio/duration/voice), progress UI, gallery/My Videos grid, color/typography/motion choices, copy tone.
- Produce specs/001-video-generation/design-system.md: color tokens (light + dark), typography scale, spacing, radius, shadows, motion guidelines, and component list using shadcn/ui. Premium, modern, dark-first look but equally polished light mode. Do not copy any brand's logos, names or assets.

## Outputs
plan.md, research.md, data-model.md, contracts/ (OpenAPI for all endpoints), quickstart.md (local setup in Ubuntu/WSL), design-system.md. Run the Constitution Check before and after design. Do not write application code yet.

## Response snapshot

Ran `setup-plan.sh`, then produced all six requested artifacts under `specs/001-video-generation/`:

- **plan.md**: Technical Context (TS/Node 20 frontend, Python 3.12 backend/worker/GPU-worker, pytest scoped to 3 critical paths per Constitution VII); Constitution Check table (8/8 principles PASS, one PASS-WITH-JUSTIFICATION on Principle VI); a 4-directory monorepo structure (`frontend/`, `backend/`, `gpu-worker/`, `infra/`) replacing the template's single/2-tier options; Complexity Tracking with two justified entries (gpu-worker as a 4th deployable; GPU→R2 presigned-URL uploads bypassing the backend for raw intermediate clips/audio only, with the FFmpeg merge/final-upload still backend-side); a Post-Design Re-check confirming Phase 1 artifacts introduced no new violations.
- **research.md**: 10 backend/infra decisions (A1–A10: Redis-backed session over JWT, Resend as the email provider, row-locked idempotent job creation, ComfyUI API-format workflow invocation, single-pass OmniVoice narration, atempo-then-fail narration fit, stale-job sweeper as a plain loop, VIDEO_PROVIDER=mock sharing the real FFmpeg path, moderation + structured-output retry-once, 3s polling over WebSockets) each in Decision/Rationale/Alternatives format; plus Section B UI design research — live-fetched Runway, Pika, and Higgsfield landing pages and searched Kling/Luma/Hailuo duration-and-aspect-ratio UI conventions, synthesized into a dark-first-but-equal-light-mode decision with sources cited.
- **data-model.md**: Student, VideoJob (with embedded JSONB `scenes`, full state-transition diagram queued→…→ready/failed), Password Reset Token (hash-only storage, invalidation-on-reissue), Usage Counter (composite PK `(student_id, usage_date)`, the row locked for atomic limit enforcement); a documented decision to NOT persist script drafts server-side (stateless `/scripts`, approval payload carries the final edited script).
- **contracts/openapi.yaml**: full OpenAPI 3.0 spec — auth (register/login/logout/forgot-password/reset-password), `/me` (profile+usage), `/voices`, `/scripts` (generate/regenerate), `/videos` (create/list/get/delete/retry), with a shared `Error` schema carrying a machine-readable `code`, friendly `message`, `requestId`, and optional `resetsAt` (Principle V compliance baked into the contract).
- **quickstart.md**: Ubuntu/WSL setup — `docker-compose.dev.yml` for Postgres+Redis only, native backend (uvicorn + RQ worker + scheduler, 3 processes) and frontend, full `.env` walkthrough including why R2 credentials are still needed under `VIDEO_PROVIDER=mock`, a step-by-step flow walkthrough, and the 3-file pytest command.
- **design-system.md**: dark/light color tokens (CSS custom properties mapped to shadcn/ui's convention), typography scale including a dedicated larger-line-height `urdu-script` scale for Noto Nastaliq Urdu, spacing/radius/shadow/motion rules (with `prefers-reduced-motion` handling), and a component table mapping each UI need (option cards, word counter, progress stepper, video card, etc.) to a shadcn/ui base component.

Ran `update-agent-context.sh claude`, which updated `CLAUDE.md`'s Active Technologies / Recent Changes sections (verified the diff — appended cleanly, no corruption of existing content).

## Outcome

- ✅ Impact: Feature 001-video-generation is fully planned and ready for `/sp.tasks`; no application code was written, per instruction.
- 🧪 Tests: none run (planning stage); quickstart.md documents the 3 critical-path test files that `/sp.tasks`/implementation will need to create.
- 📁 Files: `specs/001-video-generation/{plan.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md, design-system.md}` (all created), `CLAUDE.md` (agent context updated by script)
- 🔁 Next prompts: `/sp.tasks` to break this plan into dependency-ordered, per-user-story tasks.
- 🧠 Reflection: The one real architectural judgment call was the GPU→R2 presigned-URL upload nominally brushing against Principle VI ("uploads to storage MUST run on the backend") — resolved by treating it as a narrowly-scoped credential delegation (GPU still does zero FFmpeg/merge/final-upload work) and documenting it explicitly in Complexity Tracking rather than silently waiving the principle or over-engineering a byte-relay through the backend. The competitor UI research used a mix of live WebFetch (Runway, Pika, Higgsfield — successfully fetched) and WebSearch (Kling/Luma/Hailuo, whose actual logged-in workspaces aren't publicly fetchable) to stay grounded in real, current product patterns rather than relying solely on potentially-stale internal knowledge.

## Evaluation notes (flywheel)

- Failure modes observed: one WebFetch (lumalabs.ai/dream-machine) returned text-only content with no usable visual-design detail; compensated by leaning on WebSearch comparison-article results for Luma/Kling instead, which still yielded the needed duration/aspect-ratio UI convention data point.
- Graders run and results (PASS/FAIL): Constitution Check — PASS (8/8, 1 justified exception) both pre- and post-design; manual scan of contracts/openapi.yaml and data-model.md against spec.md's FR list — PASS (no capability introduced beyond the spec, no admin-shaped surface reintroduced).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
