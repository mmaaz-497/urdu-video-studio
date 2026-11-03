---
id: 0001
title: Create Urdu Video Studio constitution
stage: constitution
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: none
branch: master
user: mmaazjatt497@gmail.com
command: /sp.constitution
labels: ["constitution", "governance", "setup"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none (no automated tests applicable to this change)
---

## Prompt

Create the constitution for "Urdu Video Studio" — a web app where students type their idea (Roman Urdu or Urdu, possibly with spelling mistakes) and get a 15-second video with Urdu narration.

Principles:
- Simple, readable code. A new developer should understand any file in 5 minutes.
- Prefer well-known libraries over custom code. Propose new dependencies before adding them.
- Every feature has its spec in specs/. The spec is the source of truth; update the spec before changing behaviour.

Stack (fixed):
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui.
- Backend: FastAPI (Python 3.12) + PostgreSQL (SQLAlchemy 2 + Alembic) + Redis + RQ worker.
- LLM: OpenAI via OpenAI Agents SDK, with Pydantic structured outputs. It fixes the student's Roman Urdu/Urdu text, writes the Urdu narration script, and writes English scene prompts.
- Video: Wan 2.2 TI2V-5B via ComfyUI on RunPod Serverless. Voice: OmniVoice Urdu fine-tune with two preset voices (male, female).
- Video assembly: FFmpeg on the backend server. Storage: Cloudflare R2 (S3-compatible).
- Video output: 15 seconds (3 clips of 5s), aspect ratio 16:9 or 9:16 chosen by the student.

Environments:
- Local development inside Ubuntu (WSL). PostgreSQL and Redis run via Docker Compose; frontend and backend run natively with hot reload.
- Production on one VPS with Docker Compose (frontend, backend, worker, PostgreSQL, Redis) behind Caddy with automatic HTTPS on our domain.
- VIDEO_PROVIDER setting: "mock" (returns bundled sample clips, no GPU cost) for development; "runpod" for real generation.

Error handling (mandatory):
- Every external call (OpenAI, RunPod, R2, FFmpeg, DB) has a timeout, a clear error message, and limited retries where safe.
- Never show raw stack traces to users. Show friendly English messages; log full details server-side with a request/job ID.
- Video jobs always end in "completed" or "failed" with a reason — never stuck in "processing". Stale jobs are detected and marked failed.

Cost rules:
- GPU is used only for GPU work (clips + voice). LLM calls, merging and uploads run on our server.
- No GPU job starts until the student approves (or edits and approves) the generated script.

Users and roles:
- Students sign up themselves with email + password. Admin role manages users and sets the daily video limit per student.

UI:
- Premium, modern look with light and dark mode, fully responsive (mobile first).
- All UI text in English; script and narration in Urdu (right-to-left rendering for Urdu text).

Security:
- All secrets in .env files, never committed; provide .env.example. Validate all user input. Passwords hashed. Enforce per-user daily limits server-side.

Testing:
- Keep tests minimal: only critical paths (auth, job status flow, LLM output parsing). No exhaustive test suites.

Licensing:
- OmniVoice weights are CC-BY-NC: this app is for non-commercial educational use only.

Definition of done:
- Behaviour matches the spec, including error cases. Runs locally with documented setup steps in README.

## Response snapshot

Filled `.specify/memory/constitution.md` (initial ratification, version 1.0.0, ratified and amended 2026-11-02), replacing all template placeholders. Structure:

- **Core Principles (I–VIII)**: Simplicity & Readability (NON-NEGOTIABLE), Library-First/Propose-Before-Adding, Spec Is the Source of Truth, Fixed Technology Stack (frontend/backend/LLM/video/voice/assembly/storage/output contract), Fail Loud Fail Clear (timeouts/retries/no raw stack traces/jobs never stuck in processing), GPU Cost Discipline & Student Approval Gate, Minimal Critical-Path Testing, Non-Commercial Educational Use Only (OmniVoice CC-BY-NC).
- **Technology Stack & Environments** section: WSL local dev with Docker Compose for Postgres/Redis, single-VPS production with Caddy/HTTPS, `VIDEO_PROVIDER` mock/runpod switch, Definition of Done.
- **Security, Access & UI Standards** section: .env/.env.example secrets, server-side validation, password hashing, student/admin roles with server-enforced daily limits, premium responsive UI with light/dark mode, English UI copy with RTL Urdu script/narration.
- **Governance** section: amendment procedure via `/sp.constitution`, semantic versioning policy for governance changes, compliance review tied to `/sp.plan` Constitution Check gate.

Prepended a Sync Impact Report HTML comment documenting the version bump (none → 1.0.0), added sections, and template-alignment check. Verified `plan-template.md`, `spec-template.md`, and `tasks-template.md` require no structural changes since their Constitution Check / FR / phase sections already reference the constitution generically. Flagged one pending follow-up: no `README.md` exists yet, which Principle/DoD text requires once runnable code lands.

## Outcome

- ✅ Impact: Initial project constitution ratified at v1.0.0; establishes non-negotiable guardrails (stack, error handling, cost gating, licensing) that all future specs/plans/ADRs must comply with.
- 🧪 Tests: none (governance document; no automated tests apply)
- 📁 Files: `.specify/memory/constitution.md` (created/overwritten with full content)
- 🔁 Next prompts: Run `/sp.specify` for the first feature (likely "student video request flow" or "auth & roles"); create `README.md` with local setup steps once scaffolding exists.
- 🧠 Reflection: User input was comprehensive and unambiguous, so no clarifying questions were needed; all template placeholders were resolved from the provided brief without invented details.

## Evaluation notes (flywheel)

- Failure modes observed: none — single-pass fill, no unresolved placeholders.
- Graders run and results (PASS/FAIL): manual placeholder-scan — PASS (no remaining `[ALL_CAPS]` tokens); date format ISO check — PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
