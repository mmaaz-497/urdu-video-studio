<!--
Sync Impact Report
Version change: 2.0.0 → 2.0.1 (PATCH — wording/changelog cleanup only; no
  principle text, stack, or governance rule changed)
Modified principles: none.
Added content: none.
Removed sections/content:
  - The v2.0.0 Sync Impact Report's "Downstream artifacts flagged" note (which
    warned that specs/001-video-generation/spec.md still specified an Admin
    role and a fixed-duration-only video contract) is removed: that artifact
    has since been rewritten to match v2.0.0 (single `student` role,
    student-selectable 5/10/15s duration) and the note was stale.
Templates requiring updates: none (no principle changed).
Downstream artifacts flagged: none outstanding.
Follow-up TODOs: none.
-->

# Urdu Video Studio Constitution

## Core Principles

### I. Simplicity & Readability (NON-NEGOTIABLE)

Code MUST be simple enough that a new developer understands any single file within
five minutes. Functions and modules MUST have one clear responsibility; clever or
compact code that sacrifices clarity is prohibited. When a simple approach and a
clever approach both solve the problem, the simple approach MUST be chosen.

**Rationale**: This is a student-facing educational project likely to be read, extended,
and maintained by learners and contributors with varying experience levels. Readability
is the primary defense against accumulating complexity debt.

### II. Library-First, Propose-Before-Adding

Well-known, actively maintained libraries MUST be preferred over custom
implementations for solved problems (auth, validation, HTTP clients, queues, ORM,
etc.). Any new dependency not already part of the fixed stack (see Technology Stack)
MUST be proposed explicitly — naming the library, the problem it solves, and the
alternative considered — before it is added to `package.json`, `requirements.txt`,
or equivalent manifests.

**Rationale**: Prevents silent scope/dependency creep and keeps the dependency graph
auditable and intentional.

### III. Spec Is the Source of Truth

Every feature MUST have a corresponding spec under `specs/<feature>/spec.md`. The
spec MUST be updated BEFORE behavior changes — not after. Code review and
implementation MUST treat the spec as authoritative; if implementation and spec
diverge, the spec is updated first, then the code follows.

**Rationale**: Keeps business intent and technical implementation traceable and
prevents undocumented behavior drift, consistent with this project's Spec-Driven
Development workflow (PHRs, ADRs, `/sp.*` commands).

### IV. Fixed Technology Stack

The technology stack is fixed and MUST NOT be substituted without a constitution
amendment (see Governance):

- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui.
- **Backend**: FastAPI (Python 3.12) + PostgreSQL via SQLAlchemy 2 + Alembic
  migrations + Redis + RQ worker for background jobs.
- **LLM**: OpenAI via the OpenAI Agents SDK, using Pydantic structured outputs,
  for three jobs only: (1) correcting the student's Roman Urdu/Urdu input text,
  (2) writing the Urdu narration script, (3) writing English scene prompts for the
  video model.
- **Video generation**: Wan 2.2 TI2V-5B via ComfyUI, run on RunPod Serverless.
- **Voice**: OmniVoice Urdu fine-tune, two preset voices (male, female).
- **Video assembly**: FFmpeg, executed on the backend server (not on GPU).
- **Storage**: Cloudflare R2 (S3-compatible).
- **Email**: a transactional email service (provider selected during planning) used
  solely to deliver password-reset emails in this version.
- **Video output contract**: duration is chosen by the student as 5, 10, or 15
  seconds (1, 2, or 3 clips of 5 seconds each); aspect ratio is 16:9 or 9:16,
  also chosen by the student. The final rendered video MUST NEVER exceed 15
  seconds, regardless of student selection or any processing fallback.

**Rationale**: A fixed stack removes an entire class of architectural debate from
every feature spec and keeps local/production parity achievable by one small team.
Making duration student-selectable (while capping it hard at 15s) gives flexibility
without reopening the cost/complexity trade-offs the 15-second ceiling was chosen to control.

### V. Fail Loud, Fail Clear

Every external call — OpenAI, RunPod, Cloudflare R2, FFmpeg invocations, the
transactional email service, and database queries — MUST have an explicit
timeout, a clear error message, and a bounded retry policy where retries are
safe (idempotent operations only). Raw stack traces or internal exception
details MUST NEVER be shown to end users; users see friendly English messages
while full details are logged server-side tagged with a request ID or job ID.
A video job MUST always terminate in either `completed` or `failed` with a
reason — it MUST NEVER remain stuck in `processing`. A background process MUST
detect and mark stale/orphaned jobs as `failed`.

**Rationale**: Video generation involves multiple unreliable external services
(GPU provider, LLM API, object storage, email delivery); students need a
trustworthy status signal, and operators need traceable failures, not silent hangs.

### VI. GPU Cost Discipline & Student Approval Gate

GPU resources (RunPod Serverless) MUST be used only for GPU-bound work: clip
generation and voice synthesis. LLM calls, video/audio merging (FFmpeg), and
uploads to storage MUST run on the backend server, never on GPU. No GPU job
MUST be started until the student has explicitly approved the generated script
(or edited it and then approved the edited version).

**Rationale**: GPU time is the dominant cost driver; gating it behind explicit
student approval prevents wasted spend on scripts the student would have
rejected anyway.

### VII. Minimal, Critical-Path Testing

Automated tests are REQUIRED only for critical paths: authentication (including
password reset), the video job status state machine, and LLM structured-output
parsing. Exhaustive test suites or speculative coverage of non-critical paths
are explicitly NOT required and SHOULD be avoided as an engineering-time sink.

**Rationale**: Matches a small-team, fast-iteration educational project; testing
investment is targeted at the paths where a silent failure would be most costly
(security, stuck jobs, broken parsing), not spread thin.

### VIII. Non-Commercial Educational Use Only

The OmniVoice voice weights used in this project are licensed CC-BY-NC. The
application, and any deployment of it, MUST be operated strictly for
non-commercial educational use. No feature, pricing model, or deployment
decision MUST introduce commercial use of generated audio/video without first
revisiting this license constraint.

**Rationale**: Direct legal constraint inherited from the voice model's license;
violating it exposes the project to licensing liability.

## Technology Stack & Environments

- **Local development**: Ubuntu via WSL. PostgreSQL and Redis run in Docker
  Compose; frontend (Next.js) and backend (FastAPI) run natively with hot reload
  for fast iteration.
- **Production**: a single VPS running Docker Compose with five services —
  frontend, backend, worker, PostgreSQL, Redis — behind Caddy, which provides
  automatic HTTPS on the project's domain.
- **`VIDEO_PROVIDER` setting**: a server-side environment switch with two valid
  values — `mock` (returns bundled sample clips, zero GPU cost; default for
  development) and `runpod` (real generation via RunPod Serverless; used in
  production). Application code MUST branch on this setting rather than
  detecting environment implicitly.
- **Daily limits are server configuration, not admin-managed**: `DAILY_VIDEO_LIMIT`
  and `DAILY_SCRIPT_LIMIT` environment variables set the per-student daily caps
  platform-wide. There is no in-app role that can override these per student;
  changing them requires changing server configuration. Both are enforced
  server-side and reset at midnight Asia/Karachi time.
- Definition of Done for any feature includes: behavior matches its spec
  (including documented error cases), and the project runs locally following
  documented setup steps in `README.md`.

## Security, Access & UI Standards

- **Secrets**: all secrets MUST live in `.env` files that are never committed;
  an `.env.example` MUST be kept up to date for every required variable,
  including `DAILY_VIDEO_LIMIT`, `DAILY_SCRIPT_LIMIT`, and the transactional
  email provider's credentials.
- **Input validation**: all user-supplied input MUST be validated server-side
  (student free-text ideas, auth fields, password-reset requests).
- **Authentication**: passwords MUST be hashed (never stored or logged in
  plaintext). Students self-register with email + password.
- **Password reset**: students MUST be able to self-service reset a forgotten
  password via a "Forgot password" flow: a time-limited, single-use token is
  emailed to the account's address through the transactional email service
  (Principle IV); the token MUST expire after a short, fixed window and MUST be
  invalidated after first use or after a new reset is requested.
- **Authorization**: a single role — `student`. There is no admin role in this
  version; students self-register and can only view/manage their own account
  and videos. Per-student daily limits (see Technology Stack & Environments)
  MUST be enforced server-side regardless of role — client-side limit display
  is advisory only, never authoritative.
- **UI**: premium, modern visual design with both light and dark mode, fully
  responsive with a mobile-first layout. All UI chrome/copy is in English.
  Generated script and narration text is in Urdu and MUST render
  right-to-left (RTL).

## Governance

This constitution supersedes conflicting guidance in other docs, templates, or
prior practice for this project. All feature specs, plans, and PRs MUST be
checked against these principles before merge; any violation MUST be called out
explicitly in the plan's Complexity Tracking section with a justification, or
the design MUST change.

**Amendment procedure**: amendments are proposed via `/sp.constitution` with the
specific principle/section change and rationale, reviewed by the project owner,
and take effect only once written back to this file with an updated Sync Impact
Report. Dependent templates (`plan-template.md`, `spec-template.md`,
`tasks-template.md`, command files) MUST be re-checked for alignment as part of
the same amendment. Existing feature specs under `specs/` that conflict with an
amendment MUST be flagged to the user and revisited before their next `/sp.plan`
or `/sp.tasks` run.

**Versioning policy** (semantic versioning applied to governance):
- **MAJOR**: backward-incompatible principle removal or redefinition (e.g.,
  changing the fixed technology stack, removing the non-commercial constraint,
  adding/removing a user role, redefining the video output contract).
- **MINOR**: a new principle or materially expanded section is added.
- **PATCH**: wording clarifications, typo fixes, non-semantic refinements.

**Compliance review**: every `/sp.plan` run MUST execute the Constitution Check
gate against the principles above before Phase 0 research begins, and again
after Phase 1 design.

**Version**: 2.0.1 | **Ratified**: 2026-11-02 | **Last Amended**: 2026-11-02
