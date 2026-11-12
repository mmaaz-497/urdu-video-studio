# Implementation Plan: Student Video Generation

**Branch**: `001-video-generation` | **Date**: 2026-11-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-video-generation/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

A single-role (student-only) web app where a student types an idea in Roman
Urdu/Urdu, picks a duration (5/10/15s), aspect ratio (16:9/9:16), and a preset
voice, gets an LLM-generated Urdu script + scene breakdown to review/edit/approve
behind a live word-counter gate, then a GPU pipeline (Wan 2.2 TI2V-5B via ComfyUI
on RunPod + OmniVoice Urdu TTS) renders 1–3 five-second clips and narration that
the backend assembles with FFmpeg into a final MP4 (never exceeding 15s), uploads
to Cloudflare R2, and exposes through a polling-based progress view and a "My
Videos" library. Daily video/script quotas come from server env config
(`DAILY_VIDEO_LIMIT`, `DAILY_SCRIPT_LIMIT`), enforced atomically per student.
Self-service password reset is delivered via a transactional email provider.

## Technical Context

**Language/Version**: TypeScript 5.x on Node.js 20+ (frontend); Python 3.12
(backend API, RQ worker, and the separately-deployed GPU worker)
**Primary Dependencies**:
- Frontend: Next.js (App Router), Tailwind CSS, shadcn/ui, TanStack Query
  (polling), next-themes (light/dark), react-hook-form + zod (forms/validation),
  next/font (Noto Nastaliq Urdu for RTL script rendering).
- Backend: FastAPI, SQLAlchemy 2 + Alembic, Redis + RQ, OpenAI Agents SDK +
  Pydantic (structured LLM output), argon2-cffi (password hashing), an S3-
  compatible client (boto3) for Cloudflare R2, a transactional email SDK (see
  research.md for provider choice), the `ffmpeg` CLI invoked as a subprocess.
- GPU worker (separate deployable): `runpod` Python SDK (serverless handler),
  headless ComfyUI running the official Wan 2.2 TI2V-5B API-format workflow,
  OmniVoice Urdu fine-tune (`mlwithabdullah/omnivoice-urdu-6000`) inference code.
**Storage**: PostgreSQL (students, video jobs, scenes, password reset tokens,
usage counters); Redis (RQ queue, session store); Cloudflare R2 (raw clips/audio,
final MP4s, thumbnails, bundled mock-mode sample assets).
**Testing**: pytest (+ pytest-asyncio) on the backend, scoped per Constitution
Principle VII to three critical paths only — authentication (incl. password
reset), the video job status state machine, and LLM structured-output parsing/
validation. No dedicated frontend test framework is introduced for this feature;
TypeScript's compiler and ESLint provide static safety, consistent with minimal
critical-path testing.
**Target Platform**: Linux server — a single *shared* cPanel/WHM VPS (AlmaLinux 8,
rootful Podman 4.9 driven by the Docker Compose binary over `podman.socket`, behind
the host's existing Apache EA4 reverse proxy with cPanel AutoSSL; see Design Revision
2026-11-12) for frontend/backend/worker/scheduler/Postgres/Redis; Ubuntu via WSL2 for local development;
RunPod Serverless (ephemeral GPU containers, not a persistent server) for the GPU
worker.
**Project Type**: Web application with a separate GPU-worker deployable — a
4-directory monorepo (frontend / backend / gpu-worker / infra), not the
template's single-project or 2-tier web option (see Project Structure below).
**Performance Goals**: Review screen appears within ~30s of idea submission
(SC-005); non-LLM/non-GPU API endpoints target p95 < 500ms; client polls job
status every 3s (TanStack Query `refetchInterval`), a load level trivial for a
single-VPS Postgres/Redis pair at this project's expected scale. Per
Constitution Principle VII (minimal, critical-path testing), neither budget
gets dedicated load-testing or latency-instrumentation tasks in v1 — both are
spot-checked manually during the quickstart walkthrough (see
`quickstart.md`'s manual performance/responsiveness check) rather than
continuously measured; revisit with real instrumentation only if a student-
reported slowness surfaces in production.
**Constraints**: Final video duration MUST exactly equal the student's chosen
duration and MUST NEVER exceed 15 seconds under any fallback path (Constitution
Principle IV); no GPU-bound work may start before explicit student approval
(Principle VI); OmniVoice's CC-BY-NC license restricts the whole deployment to
non-commercial educational use (Principle VIII); both daily limits MUST be
enforced server-side, atomically, with no client-side bypass path.
**Scale/Scope**: Single small-to-mid-size educational deployment (expected low
hundreds of active students, not a multi-tenant SaaS); video job concurrency
bounded by RunPod Serverless concurrency and the single VPS's FFmpeg/CPU capacity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Simplicity & Readability | ✅ PASS | 4-directory monorepo, no speculative abstractions; session handling reuses the already-present Redis instead of adding JWT machinery (see research.md). |
| II | Library-First, Propose-Before-Adding | ✅ PASS (with proposals) | New libraries beyond the fixed stack — TanStack Query, next-themes, react-hook-form, zod, argon2-cffi, the `runpod` SDK, an email-provider SDK — are each proposed with rationale in research.md before use; all are well-known, actively maintained. |
| III | Spec Is the Source of Truth | ✅ PASS | This plan is derived directly from `spec.md` (already aligned to constitution v2.0.0); no behavior is introduced here that isn't traceable to an FR/edge case. |
| IV | Fixed Technology Stack | ✅ PASS | Uses exactly the mandated stack (Next.js/TS/Tailwind/shadcn; FastAPI/Postgres/SQLAlchemy2/Alembic/Redis/RQ; OpenAI Agents SDK; Wan 2.2 TI2V-5B via ComfyUI/RunPod; OmniVoice Urdu, 2 voices; FFmpeg on the backend; R2; a transactional email provider; 5/10/15s duration capped at 15s). |
| V | Fail Loud, Fail Clear | ✅ PASS | Every external call (OpenAI, RunPod, R2, FFmpeg, email, DB) gets an explicit timeout + bounded retry in research.md; a stale-job sweeper guarantees no job stays "processing" forever; errors surfaced to students are always friendly-English, full detail logged server-side with the job/request ID. |
| VI | GPU Cost Discipline & Student Approval Gate | ⚠️ PASS WITH JUSTIFICATION | GPU work starts only post-approval and is limited to clip + voice generation; FFmpeg assembly and the *final* MP4/thumbnail upload run on the backend. One narrow exception — the GPU worker PUTs its *raw intermediate* clips/audio directly to R2 via short-lived, key-scoped presigned URLs instead of returning them to the backend first. Justified in Complexity Tracking below. |
| VII | Minimal, Critical-Path Testing | ✅ PASS | Test plan limited to auth/password-reset, the job state machine, and LLM output parsing — matching the principle exactly, nothing broader added. |
| VIII | Non-Commercial Educational Use Only | ✅ PASS | No payment/commercial feature is introduced anywhere in this plan. |

No blocking violations. One justified exception is recorded in Complexity Tracking.

**Post-Design Re-check (after Phase 1 — research.md, data-model.md,
contracts/openapi.yaml, quickstart.md, design-system.md)**: Re-reviewed all
eight principles against the completed design artifacts. No new violations were
introduced: `data-model.md` adds no entity or field outside the spec's Key
Entities; `contracts/openapi.yaml` exposes no capability beyond the spec's FRs
(no admin-shaped endpoints, no per-student limit override endpoint); the session
and email-provider choices in `research.md` stayed within Principle II's
propose-before-adding discipline; `design-system.md` only styles the UI
standard already required (Principle "Security, Access & UI Standards") and
introduces no new runtime dependency. The single justified exception (presigned
GPU→R2 upload) is unchanged by Phase 1 design. **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-video-generation/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── design-system.md     # Phase 1 output (/sp.plan command) — UI tokens & components
├── contracts/           # Phase 1 output (/sp.plan command) — OpenAPI
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
frontend/
├── app/
│   ├── (public)/                # landing page, FAQ, theme-aware marketing routes
│   ├── (auth)/login/ register/ forgot-password/ reset-password/
│   └── (app)/create/ review/ videos/[id]/progress/ videos/  # authenticated routes
├── components/
│   ├── ui/                      # shadcn/ui primitives
│   └── studio/                  # option cards, word counter, progress stepper, video grid
├── lib/
│   ├── api-client.ts            # typed fetch wrapper over the backend OpenAPI contract
│   ├── queries/                 # TanStack Query hooks (scripts, videos, usage)
│   └── utils/
├── styles/                      # Tailwind config, RTL/Urdu font setup
└── public/                      # sample landing-page videos, static assets

backend/
├── app/
│   ├── main.py                  # FastAPI entrypoint (HTTP API)
│   ├── worker.py                # RQ worker entrypoint (video pipeline jobs)
│   ├── scheduler.py             # periodic stale-job sweeper
│   ├── core/                    # config, DB session, security (hashing, sessions)
│   ├── models/                  # SQLAlchemy models (Student, VideoJob, Scene, …)
│   ├── schemas/                 # Pydantic request/response + LLM structured-output schemas
│   ├── api/                     # routers: auth, scripts, videos, usage, voices
│   └── services/                # llm_service, moderation_service, video_pipeline,
│                                 # storage_service (R2), email_service, mock_provider
├── alembic/                      # migrations
└── tests/
    ├── test_auth.py
    ├── test_video_job_state_machine.py
    └── test_llm_output_parsing.py

gpu-worker/
├── handler.py                   # RunPod Serverless entrypoint
├── workflows/wan22_ti2v5b.json   # ComfyUI API-format workflow template
├── omnivoice/                   # inference wrapper + 2 preset reference-voice assets
└── requirements.txt

infra/
├── docker-compose.dev.yml       # Postgres + Redis only (frontend/backend run natively)
├── docker-compose.prod.yml      # frontend, backend, worker, scheduler, postgres, redis (podman)
├── uvs.sh                       # VPS wrapper: the only way compose is ever invoked there
├── deploy.sh                    # runs on the dev machine: build, ship, migrate, restart, check
├── deploy.env.example           # VPS_HOST / VPS_PORT for deploy.sh (real file gitignored)
├── .env.production.example      # every production variable (real .env only on the VPS)
├── apache/urdu-video-studio.conf  # cPanel EA4 userdata include (reverse proxy)
└── backup/uvs-backup.sh         # daily pg_dump, 7-day retention (root cron)
```

**Structure Decision**: A 4-directory monorepo (`frontend/`, `backend/`,
`gpu-worker/`, `infra/`) rather than the template's single-project or 2-tier
web-app layout. `gpu-worker/` must be its own deployable because it ships as a
RunPod Serverless container bundling ComfyUI plus multi-gigabyte Wan 2.2/OmniVoice
model weights — a fundamentally different runtime and deploy cadence from the
lightweight FastAPI backend/RQ worker. `infra/` centralizes the Compose file,
Apache proxy include and deploy/backup scripts shared across the deployable services.

## Design Revision 2026-11-07: per-scene narration and attachment downloads

**Problem 1 — narration was not synced to visuals.** One `urdu_script` explained the
idea while separate English scene prompts showed something else, with one TTS file laid
over the whole video. **Decision:** the unit of generation is the *scene*.

- **Data contract**: `scenes[] = {visualPrompt, narrationUr}` (API camelCase). `urdu_script`
  stays as the narrations joined in order (derived server-side, display/back-compat). The
  `video_jobs.scenes` column is already JSONB, so **no migration**; legacy string rows are
  normalised on read and are not retryable (their narration cannot be recovered).
- **LLM** (`llm_service.py`): one structured output with `scenes[].{visual_prompt,
  narration_ur}` written together; narration = what is visible, present tense, simple Urdu;
  the visual prompt depicts exactly that narration; no on-screen text. The limit
  `WORDS_PER_5S_MAX` (12) is enforced **per scene**; the existing retry-with-feedback (names
  the offending scenes) and sentence-boundary trim now run per scene; Roman-Urdu (Latin
  letter) checks apply to `corrected_idea` and every `narration_ur`.
- **Review UI**: one card per scene (visual prompt + RTL editable narration + its own word
  counter); Approve is disabled if any scene is over limit/empty. Approval gate unchanged: no
  GPU spend before approval.
- **GPU worker**: job input `scenes[] = {visual_prompt, narration}`; presigned PUT URLs
  `clips[]` and `narrations[]` (one per scene); OmniVoice runs once per scene (model loaded once,
  released after); output `narration_durations_seconds[]`. **This changes the worker contract,
  so the worker image must be rebuilt and the endpoint updated** (backend and worker ship together).
- **Assembly** (`ffmpeg_service.build_scene_narration_track`): each scene's narration is
  sped up by at most `MAX_NARRATION_SPEEDUP` (1.10) if longer than 5 s, padded with silence to
  exactly 5 s, then all scenes are concatenated; the track is muxed over the concatenated clips.
  A scene that still does not fit → `SCRIPT_TOO_LONG` (unchanged failure semantics). The mock
  provider uses the same path with one bundled narration per scene.

**Problem 2 — Download expanded the player.** Root cause (confirmed with Playwright, see
tasks T100): the HTML `download` attribute is ignored for cross-origin URLs, and the R2
presigned URL is cross-origin, so the click navigated the tab to the raw MP4 and the browser's
built-in video viewer opened. **Decision:** `GET /videos/{id}/download` (owner-only, same
auth as the video) returns a short-lived URL whose response carries
`Content-Disposition: attachment; filename="<safe-ascii>.mp4"` — R2 presign with
`ResponseContentDisposition` (SigV4); local storage returns an HMAC-signed, expiring URL to a
backend endpoint serving a `FileResponse` attachment. The button is a real `<button>`: it fetches
the URL then clicks a hidden anchor; the player element is never touched.

## Design Revision 2026-11-12: production on a shared cPanel/WHM VPS (Phase 8)

The production host is **not** a clean VPS: AlmaLinux 8.10 with cPanel/WHM and 12 live
sites; Apache (EA4) owns :80/:443; 2 vCPU / 3.8 GB RAM, already swapping; no Docker
(`docker` is the podman-docker shim) and Podman 4.9.4 already runs other projects'
containers (`tokoshopee-postgres` on 127.0.0.1:5432, `fiv-cobalt` on 127.0.0.1:4201);
127.0.0.1:3000 and :8000 are taken; no host firewall; SELinux disabled.

- **Caddy is dropped.** Apache must keep :80/:443 for the existing sites, and cPanel
  AutoSSL issues the certificate. A per-domain EA4 *userdata include*
  (`infra/apache/urdu-video-studio.conf`) proxies `/api/` → `127.0.0.1:8100/` (prefix
  stripped, exactly like the dev rewrite) and everything else → `127.0.0.1:3100`, same
  origin, excluding `/.well-known/` so AutoSSL's HTTP validation keeps working. Apache's
  proxy modules are already loaded; no EA4 module installs.
- **Containers: rootful Podman, never docker-ce** (on EL8 installing docker-ce removes
  podman and would break the other projects' containers).
- **Compose tool: the Docker Compose standalone binary (v5.7.1, pinned) over
  `podman.socket`, not podman-compose.** Verified on AlmaLinux 8.10 + podman 4.9.4 +
  EPEL (2026-11-12) with this exact compose file:
  - EPEL 8 ships podman-compose **1.0.6**, which (a) turns `depends_on: condition:
    service_healthy` into plain `--requires` (start order only, no health wait), (b)
    rewrites exec-form healthchecks into an invalid shell string so backend/frontend stay
    unhealthy forever, and (c) silently ignores `memswap_limit` (podman then allows swap
    = 2× memory on an already-swapping host).
  - Docker Compose over the socket waited for postgres/redis **Healthy** before starting
    the app, applied `mem_limit`+`memswap_limit`, log caps, network aliases and
    `restart: always`, and `down` left unrelated containers untouched; a full mock job
    then ran end-to-end through 127.0.0.1:3100.
  - Found during that test: podman 4.9's compat API **re-splits exec-form healthcheck
    arguments on spaces**, so every healthcheck is written in `CMD-SHELL` form.
  - Cost: `podman.socket` must be enabled (root-only unix socket).
- **Isolation.** Every container/volume/network is named `uvs-*`; the project name is
  pinned (`name: uvs` + `-p uvs`); compose is only ever run through `/opt/uvs/uvs`
  (`infra/uvs.sh`), which also pins the file, tag and socket. Published ports bind
  `127.0.0.1` only (`3100` frontend, `8100` API); Postgres and Redis publish nothing.
- **Protecting the live sites.** Per-service memory caps with swap disabled per
  container, measured under load (two back-to-back 3-scene jobs + parallel page loads):
  postgres 160 MB, redis 64 MB (`maxmemory 32mb`, `noeviction`), backend 224 MB, worker
  624 MB (measured peak 364–423 MB — ffmpeg's concat filter holds every clip's frames),
  scheduler 80 MB (measured peak 60 MB while sweeping, +30%), frontend 128 MB =
  **1280 MB (1.25 GiB)**. The scheduler stays small only because `video_job_service`
  imports `llm_service` (OpenAI Agents SDK, ~100 MB) lazily inside `create_job`. ffmpeg is capped at
  `FFMPEG_THREADS=2` (decoders, filters, encoder) and the whole worker runs under
  `nice -n 10`. Container logs are capped at 10 MB each.
- **Reboot safety without rebooting.** Every deploy/rollback/check verifies that all six
  `uvs-*` containers exist and have restart policy `always` and that
  `podman-restart.service` is enabled — the server is never rebooted just to test this.
- **No builds on the VPS.** A Next.js build would starve the live sites of RAM. Images
  are built on the dev machine (`infra/deploy.sh`), tagged with the git short SHA and
  streamed with `docker save | gzip | ssh … podman load`; an image whose ID the VPS
  already has is re-tagged instead of re-uploaded. Rollback = re-point to the previous
  tag (schema migrations are forward-only and not rolled back).
- **Testable before DNS.** The Next.js `/api/*` rewrite is kept and baked at build time
  with `BACKEND_ORIGIN=http://backend:8000` (internal network), so the whole app works
  through `ssh -L 3100:127.0.0.1:3100` + `http://localhost:3100`; Secure cookies are sent
  to `http://localhost` by Chrome, so `COOKIE_SECURE=true` stays.
- **Proxy headers.** Uvicorn runs with `--proxy-headers` and `FORWARDED_ALLOW_IPS=*`; safe
  because the API port is reachable only from 127.0.0.1 and the private stack network.
  Cookies are always `Secure` in production (`COOKIE_SECURE`) and CSRF is double-submit,
  so neither depends on the forwarded scheme.
- **Boot.** `podman-restart.service` (already enabled) starts every `restart: always`
  container at boot without ordering; the app converges by restarting until
  Postgres/Redis are up (simulated: all healthchecks green ~15 s after an unordered start).
- **Backups.** Root cron runs `pg_dump -Fc` daily into `/opt/uvs/backups`, keeping 7 days.

## Known Risks

- **Worker memory scales with clip count/resolution.** ffmpeg's concat filter keeps every
  input's decoded frames in memory; 3 × 5 s 720p clips peak at ~420 MB of the worker's
  624 MB cap. A longer max duration or higher resolution needs re-measuring, or a
  per-clip normalize + concat-demuxer pipeline.
- **Scheduler cap depends on a lazy import.** `video_job_service` must keep importing
  `llm_service` inside `create_job`; a module-level import would pull the Agents SDK into
  the scheduler (~120 MB) and get it OOM-killed at its 80 MB cap.

- **`WORDS_PER_5S_MAX` (words-per-5-seconds narration limit, `backend/app/services/llm_service.py`) was calibrated against real OmniVoice output on 2026-11-05: it is now `12` (previously an uncalibrated estimate of 15, set when Phase 3 ran entirely in `VIDEO_PROVIDER=mock`).** Measured speech rate on the two preset voices: male mean 2.62 words/s (min 2.42), female mean 2.58 words/s (min 2.26). At 12 words per 5 s scene, mean speech takes ~4.6–4.7 s and even the slowest measured sample takes ~5.3 s, so narration fits without speed-up in the normal case and the 1.10× `atempo` (5.5 s) is only a rare safety net. (`scripts/calibrate_words.py` recommended 13, which would rely on `atempo` for most jobs and sit near the `SCRIPT_TOO_LONG` edge, so 12 was chosen deliberately.) The original risk text follows for context: This constant drives the `wordLimit` shown to students and the hard gate enforced on `POST /videos`. If it's wrong, every real (`VIDEO_PROVIDER=runpod`) job fails systematically: too generous and OmniVoice's real narration will routinely exceed the 10% `atempo` speedup budget, landing jobs in `SCRIPT_TOO_LONG`; too strict and scripts are needlessly short. Re-measure if the voices, the TTS model, or the sentence style change — see research.md A9.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| A 4th top-level deployable (`gpu-worker/`, separate from `backend/`) | RunPod Serverless requires a standalone container with ComfyUI + the Wan 2.2 TI2V-5B and OmniVoice model weights (multiple GB) baked in or mounted. | Folding this into `backend/` would force every backend deploy (a simple FastAPI bug fix, say) to rebuild/ship a multi-GB image and pull in ComfyUI's dependency tree, slowing VPS deploys for unrelated changes and violating Principle I's simplicity goal more than a 4th directory does. |
| GPU worker uploads raw intermediate clips/audio directly to R2 via presigned PUT URLs, rather than returning bytes to the backend for it to upload (Principle VI nominally reserves storage writes for the backend) | RunPod Serverless job outputs are JSON payloads with practical size/latency limits; a 5–15s video clip at 1280×704/24fps is several MB, and 1–3 clips plus a voice track would need base64 encoding (~33% size inflation) to travel through the RunPod output channel and then back out through the backend — adding materially to per-job latency and backend memory pressure for no behavioral benefit. | Routing raw clip bytes through the backend (decode RunPod's base64 output, re-upload to R2) was rejected: it adds a slow, memory-heavy hop that does nothing but relay bytes. The *intent* of Principle VI — GPU time reserved for GPU-bound compute, assembly/merge logic kept on the backend — is preserved: FFmpeg normalization, concatenation, voice-speed correction, the 15s hard cap, thumbnailing, and the *final* MP4/thumbnail upload all still happen on the backend server. The presigned URL is a narrowly-scoped, time-limited write credential for this job's specific object keys only — not general storage access from GPU code. |
