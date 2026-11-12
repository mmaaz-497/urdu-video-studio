---

description: "Task list for Student Video Generation (001-video-generation)"
---

# Tasks: Student Video Generation

**Input**: Design documents from `/specs/001-video-generation/` (plan.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md, design-system.md)
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/openapi.yaml ✅, research.md ✅, quickstart.md ✅, design-system.md ✅

**Tests**: Per Constitution Principle VII, automated tests are included for exactly
three critical paths — authentication (incl. password reset), the video job
status state machine, and LLM structured-output parsing. No other test tasks
are generated.

**Ordering** (per explicit instruction): Setup → Foundational → User Story 1
(P1, built end-to-end in `VIDEO_PROVIDER=mock` mode — zero GPU cost) → User
Story 2 (P2) → User Story 3 (P3) → User Story 4 (P4) → **Real GPU Pipeline**
(RunPod + ComfyUI + Wan 2.2 + OmniVoice — a separate later phase) → **Production
Deployment** (final phase).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 / US2 / US3 / US4 — present only on user-story-phase tasks
- Every task names exact file path(s) and the FR(s) it satisfies
- Every task that calls an external service (OpenAI, RunPod, R2, FFmpeg, Redis,
  Postgres, the email provider) states its timeout/retry/friendly-error handling

## Path Conventions

4-directory monorepo per `plan.md`: `frontend/`, `backend/`, `gpu-worker/`, `infra/`.

---

## Phase 1: Setup

**Purpose**: Repo skeleton, project scaffolding, environment configuration.

- [X] T001 Create monorepo skeleton directories: `frontend/`, `backend/app/`, `backend/alembic/`, `backend/tests/`, `gpu-worker/`, `infra/` (with `.gitkeep` in any that start empty)
- [X] T002 [P] `backend/pyproject.toml` — Python 3.12 project; pin `fastapi`, `uvicorn[standard]`, `sqlalchemy>=2`, `alembic`, `redis`, `rq`, `argon2-cffi`, `boto3`, `resend`, `pydantic>=2`, `openai-agents`, `httpx`, `python-dotenv`, plus `ruff`/`black` dev config sections
- [X] T003 [P] `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/tailwind.config.ts` — Next.js (App Router) + TypeScript + Tailwind; run `npx shadcn@latest init` to scaffold `components/ui/`
- [X] T004 [P] `gpu-worker/requirements.txt` + `gpu-worker/.gitkeep` — placeholder only; real contents built in Phase 7
- [X] T005 [P] `infra/docker-compose.dev.yml` — `postgres:16` + `redis:7` services only, with healthchecks and named volumes (constitution: frontend/backend run natively in dev)
- [X] T006 [P] `backend/.env.example` — every variable: `DATABASE_URL`, `REDIS_URL`, `VIDEO_PROVIDER` (`mock`\|`runpod`), `STORAGE_PROVIDER` (`local`\|`r2`), `LOCAL_STORAGE_PATH`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `DAILY_VIDEO_LIMIT`, `DAILY_SCRIPT_LIMIT`, `MAX_PROCESSING_SECONDS`, `RESEND_API_KEY`, `EMAIL_FROM`, `SESSION_COOKIE_SECRET`, `SESSION_TTL_SECONDS`, `CSRF_COOKIE_NAME`, `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`
- [X] T007 [P] `frontend/.env.example` — `NEXT_PUBLIC_API_BASE_URL`
- [X] T008 [P] `frontend/.eslintrc.json` + `frontend/.prettierrc` — lint/format config

**Checkpoint**: Repo skeleton exists; both sub-projects install cleanly.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: DB models + migrations, error handling/logging, session auth core,
CSRF protection, the storage abstraction (`local`/`r2`), the full design-token
system, the shared app header/nav/logout, and same-origin API wiring —
everything every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T009 `backend/app/core/config.py` — Pydantic `Settings` loading every env var from T006
- [X] T010 `backend/app/core/db.py` — SQLAlchemy 2 engine (`connect_timeout=5s`) + `sessionmaker` + `get_db` dependency; 3x startup retry with backoff; friendly `AppError("DATABASE_UNAVAILABLE")` if exhausted
- [X] T011 [P] `backend/app/models/student.py` — `Student` ORM model (data-model.md)
- [X] T012 [P] `backend/app/models/video_job.py` — `VideoJob` ORM model (status enum, JSONB `scenes`)
- [X] T013 [P] `backend/app/models/password_reset_token.py` — `PasswordResetToken` ORM model
- [X] T014 [P] `backend/app/models/usage_counter.py` — `UsageCounter` ORM model (composite PK `student_id, usage_date`)
- [X] T015 `backend/alembic.ini` + `backend/alembic/env.py` — Alembic bootstrap targeting T011–T014's metadata (depends on T011-T014)
- [X] T016 `backend/alembic/versions/0001_initial_schema.py` — initial migration: `students`, `video_jobs`, `password_reset_tokens`, `usage_counters` tables with all constraints/indexes from data-model.md (depends on T015)
- [X] T017 `backend/app/core/logging.py` — structured JSON logging + `request_id`/`job_id` contextvars (FR-034)
- [X] T018 `backend/app/core/errors.py` — `AppError` hierarchy + FastAPI exception handlers mapping every error to `{error:{code,message,requestId}}`; full exception always logged via T017, never returned to the client (FR-033, FR-034)
- [X] T019 `backend/app/core/security.py` — `argon2-cffi` `hash_password()` / `verify_password()`
- [X] T020a `backend/app/core/redis_client.py` — shared `get_redis()` factory (single `redis.asyncio.Redis` connection pool from `REDIS_URL`), used by both the session store (T020) and any Redis-backed idempotency/caching logic elsewhere (e.g., T041); every call site wraps usage with a 2s timeout + friendly `AppError("CACHE_UNAVAILABLE")` on failure — depends on T009
- [X] T020 `backend/app/core/sessions.py` — Redis-backed session store (`create_session`/`get_session`/`destroy_session`) built on T020a's shared client, httpOnly+Secure+`SameSite=Lax` cookie, `SESSION_TTL_SECONDS`; every Redis call wrapped with a 2s timeout + friendly `AppError("SESSION_STORE_UNAVAILABLE")` on failure (FR-002) — depends on T020a
- [X] T021 `backend/app/core/csrf.py` — double-submit CSRF: `issue_csrf_cookie()` sets a non-httpOnly, `SameSite=Lax` `csrf_token` cookie alongside the session cookie; `require_csrf` dependency rejects any POST/PUT/PATCH/DELETE whose `X-CSRF-Token` header doesn't match the cookie (new item #2)
- [X] T022 `backend/app/services/usage_service.py` — `get_usage_summary(student_id)` (read-only, for `GET /me`), `increment_script_count(student_id)`, `try_increment_video_count(student_id) -> bool` (row-locked `SELECT ... FOR UPDATE` on the day's `usage_counters` row, research.md A3), `decrement_video_count(student_id)` (FR-023, FR-026, FR-027, FR-028)
- [X] T023 `backend/app/services/storage_service.py` — `StorageService` protocol (`upload`, `get_download_url`, `get_presigned_put_url`, `delete`) + `get_storage()` factory switching on `STORAGE_PROVIDER` (new item #1)
- [X] T024 [P] `backend/app/services/storage_local.py` — disk-backed implementation under `LOCAL_STORAGE_PATH`, served via a `StaticFiles` mount (dev default — no R2 account needed locally)
- [X] T025 [P] `backend/app/services/storage_r2.py` — `boto3` S3-compatible client against Cloudflare R2; every call wrapped with a 10s timeout + 2 retries (exponential backoff) + friendly `AppError("STORAGE_UNAVAILABLE")` on exhaustion
- [X] T026 `backend/app/main.py` — FastAPI app: same-origin-only CORS (no cross-origin credentialed CORS needed — see T031a), session middleware (T020), CSRF middleware (T021), exception handlers (T018), static mount for local storage (T024), empty `APIRouter` includes (depends on T020, T021, T018, T024)
- [X] T027 `backend/app/schemas/common.py` — shared `Error` response schema matching `contracts/openapi.yaml`
- [X] T028 `backend/app/schemas/auth.py` — `RegisterRequest`/`LoginRequest`/`StudentProfile` schemas
- [X] T029 `backend/app/api/auth.py` — `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /me` (uses T019, T020, T021, T022); registered on T026's router (FR-001, FR-002)
- [X] T030 `backend/tests/conftest.py` — pytest fixtures: rollback-per-test DB session, `TestClient`, a student factory
- [X] T031 `backend/tests/test_auth.py` — **critical path #1**: register / login / logout / bad-credentials / session-expiry (FR-001, FR-002) — extended in Phase 5 with password-reset coverage
- [X] T031a `frontend/next.config.ts` + `frontend/.env.example` — add `rewrites()` so the browser always calls `/api/*` on the frontend's own origin, proxied server-side to the backend in development (`NEXT_PUBLIC_API_BASE_URL` default becomes `/api`, overriding T007's placeholder value); in production Apache routes `/api/*` straight to the backend container (see T094) and the rewrite remains as the SSH-tunnel fallback — makes the session/CSRF cookies truly first-party and removes any need for cross-origin, credentialed CORS (fix for same-origin API)
- [X] T032 [P] `frontend/lib/api-client.ts` — typed fetch wrapper using the relative `/api` base from T031a: `credentials: 'include'`, reads the `csrf_token` cookie into an `X-CSRF-Token` header, throws a typed `ApiError` parsed from the `Error` schema — depends on T031a
- [X] T033 [P] `frontend/components/providers/theme-provider.tsx` — `next-themes` wrapper, `defaultTheme="system"`
- [X] T033a `frontend/app/globals.css` + `frontend/tailwind.config.ts` — implement **every** design-system.md token: light + dark CSS custom properties (`--background`, `--surface`, `--foreground`, `--primary`, `--success`, `--warning`, `--destructive`, `--ring`, etc.) mapped to shadcn/ui's Tailwind color keys, `--radius-sm/md/lg`, the dark/light shadow recipes, the `display`/`h1`/`h2`/`h3`/`body`/`body-sm`/`urdu-script` type scale as Tailwind font-size utilities, Inter + Noto Nastaliq Urdu CSS font variables, and a `.urdu` utility class (`dir: rtl`, `line-height: 2`, the `urdu-script` font-size) — **every subsequent UI task MUST consume these tokens/utilities and MUST NOT hard-code colors** — depends on T003
- [X] T033b `frontend/components/layout/theme-toggle.tsx` — light/dark/system control (uses T033's `next-themes`) (FR-030) — depends on T033
- [X] T033c `frontend/components/layout/site-header.tsx` — shared nav bar: logo, "Create" + "My Videos" links and a "Logout" button when a session exists (logout calls `POST /auth/logout` via T032 then redirects to `/login`), or a "Login"/"Start Creating" link when anonymous, plus T033b's theme toggle in both states — styled entirely from T033a's tokens — depends on T033b, T032
- [X] T033d `frontend/app/(app)/layout.tsx` — mounts T033c's site-header (authenticated variant) around every `(app)/*` route, so **User Story 1 has navigation and logout from day one** — depends on T033c
- [X] T034 `frontend/app/layout.tsx` — root layout: T033's `ThemeProvider`, Inter + Noto Nastaliq Urdu font loading via `next/font` (feeding T033a's CSS variables), a `Toaster` (sonner) for friendly error banners (depends on T033, T033a)
- [X] T035 [P] `frontend/app/(auth)/login/page.tsx` — login form (react-hook-form + zod) → T032 → T029; verify mobile-first, no horizontal scroll at 375px width (FR-031)
- [X] T036 [P] `frontend/app/(auth)/register/page.tsx` — register form → T032 → T029; verify mobile-first, no horizontal scroll at 375px width (FR-031)
- [X] T037 `frontend/middleware.ts` — redirects unauthenticated requests to any `(app)/*` route to `/login`

**Checkpoint**: A student can register, log in, log out, and see the shared
header with working navigation and logout; CSRF and session cookies are
issued correctly as first-party cookies via the same-origin `/api` rewrite;
every design token exists; the storage abstraction and usage-counter helpers
are ready for every story to build on.

---

## Phase 3: User Story 1 - Create a video from an idea (Priority: P1) 🎯 MVP

**Goal**: Idea → corrected script + scenes → editable Review screen with a
live word-counter gate → approval → mock-mode processing with real FFmpeg
assembly → Ready video, playable and downloadable. Zero GPU cost
(`VIDEO_PROVIDER=mock`).

**Independent Test**: A brand-new student registers, submits an idea, approves
the generated script unedited, watches the progress view reach Ready, and
plays/downloads the finished video — unaided.

### Backend

- [X] T038 [P] [US1] `backend/app/services/moderation_service.py` — OpenAI moderation endpoint call; 10s timeout + 1 retry; `AppError("UNSAFE_CONTENT")` on a flagged result, `AppError("MODERATION_UNAVAILABLE")` friendly message if retries are exhausted (FR-008)
- [X] T039 [US1] `backend/app/services/llm_service.py` — OpenAI Agents SDK agent with a Pydantic output model (`corrected_idea`, `urdu_script`, `scenes: list[str]`, `title`); calls T038 first; server-side re-validates scene count (`= duration_seconds / 5`) and word count (≤12 words per 5s, calibrated) independently of the model's own claim; retries the generation call once on an invalid result, then `AppError("SCRIPT_GENERATION_FAILED")`; 20s timeout per LLM call (FR-007, FR-008, research.md A9) — depends on T038
- [X] T040 [P] [US1] `backend/app/schemas/scripts.py` — `GenerateScriptRequest`/`GeneratedScript` schemas
- [X] T041 [US1] `backend/app/api/scripts.py` — `POST /scripts`: requires `idempotencyKey` (edge case — double-click protection); atomically claims the Redis key `script-idem:{student_id}:{idempotencyKey}` via `SETNX` (value `"pending"`, 20s TTL matching T039's LLM timeout) *before* doing any work — if the claim fails because the key is already `"pending"`, returns 425 `REQUEST_IN_PROGRESS` immediately (a concurrent duplicate, not a replay); if the claim fails because the key already holds a cached `GeneratedScript` response, returns that cached response without re-incrementing or re-calling the LLM; if the claim succeeds, validates idea length 10–500 (FR-005), calls `usage_service.increment_script_count` under the day's row lock with a `DAILY_SCRIPT_LIMIT` check (429 `DAILY_SCRIPT_LIMIT_REACHED` if exceeded — FR-027, FR-028), calls T039, then `SET`s the same key to the final `GeneratedScript` result with a 60s TTL (overwriting `"pending"`) on success, or `DEL`s the key on failure so a legitimate retry isn't stuck behind a dead `"pending"` claim; returns `GeneratedScript` incl. `wordCount`/`wordLimit` (FR-006, FR-009, FR-010, FR-011 data contract) — depends on T039, T040, T022, T020a
- [X] T042 [P] [US1] `backend/app/api/voices.py` — `GET /voices`: static list of the 2 preset voices with preview-sample URLs (served as static assets) (FR-006)
- [X] T043 [US1] `backend/app/services/video_job_service.py` — `create_job(student, payload, idempotency_key)`: row-locked `try_increment_video_count` (usage_service), unique `(student_id, idempotency_key)` replay check (returns the existing job, no duplicate), inserts `VideoJob(status="queued")`; `get_job(id)`; `mark_status(id, status, **fields)` (FR-012, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028) — depends on T012, T022
- [X] T044 [US1] `backend/app/schemas/videos.py` — `CreateVideoJobRequest`/`VideoJob`/`VideoJobSummary`/`VideoJobStatus` schemas
- [X] T045 [US1] `backend/app/api/videos.py` — `POST /videos` (uses T043; 429 `DAILY_VIDEO_LIMIT_REACHED` with `resetsAt` on limit; 400 `SCRIPT_TOO_LONG` if the server-side word recount fails), `GET /videos/{id}` (status/progress for 3s polling) (FR-012, FR-013, FR-014, FR-015, FR-023, FR-024, FR-025, FR-026, FR-027, FR-028) — depends on T043, T044
- [X] T046 [P] [US1] `backend/app/services/mock_provider/assets/` — bundled placeholder sample clips, one set per (aspect ratio × scene count ∈ {1,2,3}) combination, plus a sample narration audio file per `voice_id`; document how these short placeholder assets were produced/sourced
- [X] T047 [US1] `backend/app/services/mock_provider.py` — `pick_assets(aspect_ratio, scene_count, voice_id)` returning file paths from T046 — depends on T046
- [X] T048 [US1] `backend/app/services/ffmpeg_service.py` — `normalize_and_concat(clips)`, `attach_narration(video, narration, max_speedup=1.10)` (raises `AppError("SCRIPT_TOO_LONG", "Script is too long for the chosen duration — please shorten it")` if still too long after the ≤10% `atempo` speedup), hard-cap to `duration_seconds`, `generate_thumbnail()`; every `ffmpeg` subprocess call has a 60s timeout + `AppError("ASSEMBLY_FAILED")` on non-zero exit/timeout (FR-017, FR-018, research.md A6)
- [X] T049 [US1] `backend/app/services/video_pipeline.py` — `run_job(job_id)` for `VIDEO_PROVIDER=mock`: `preparing` → `generating_scenes` (simulated per-scene delay + progress update using T047's assets) → `adding_voice` → `finalizing` (T048) → upload via T023/T024 → `ready`; any exception along the way marks the job `failed` with a friendly reason and calls `usage_service.decrement_video_count` (FR-013, FR-014, FR-015, FR-017, FR-018) — depends on T043, T047, T048, T023
- [X] T050 [US1] `backend/app/worker.py` — RQ worker entrypoint registering T049 as the job function; `POST /videos` (T045) enqueues the job only *after* its DB commit succeeds (research.md A3 step 5) — depends on T049
- [X] T051 [US1] `backend/app/scheduler.py` — stale-job sweeper: every `N` seconds, scans non-terminal `VideoJob` rows older than `MAX_PROCESSING_SECONDS`, marks them `failed` ("This took too long — please try again"), decrements usage via T022 (FR-015, FR-016) — depends on T012, T022

### Tests (critical paths #2 and #3)

- [X] T052 [US1] `backend/tests/test_video_job_state_machine.py` — happy path `queued→…→ready` (mock provider), idempotent-replay on duplicate `idempotencyKey`, limit-reached rejection, failed-job-not-counted, retry-creates-new-job, stale-sweeper timeout path — depends on T049, T050, T051
- [X] T053 [US1] `backend/tests/test_llm_output_parsing.py` — valid structured output accepted; invalid scene-count/word-count triggers exactly one retry then a friendly error; a moderation-flagged idea short-circuits before generation (OpenAI client mocked); a `POST /scripts` replay with the same `idempotencyKey` after completion returns the cached result without incrementing `script_count` a second time; a second request with the same `idempotencyKey` while the first is still "pending" gets 425 `REQUEST_IN_PROGRESS` and does not increment `script_count` (double-click protection, T041) — depends on T039, T041

### Frontend

> All components/pages below style exclusively via T033a's tokens/utility
> classes (no hard-coded hex colors) and render inside T033d's `(app)` layout.

- [X] T054 [P] [US1] `frontend/components/studio/option-card.tsx` — shared selectable card for duration/aspect-ratio/voice (design-system.md "Option Card")
- [X] T055 [P] [US1] `frontend/components/studio/idea-textarea.tsx` — idea input with a live 10–500 character counter
- [X] T056 [US1] `frontend/app/(app)/create/page.tsx` — Create page (rendered inside T033d's `(app)` layout, so the header/nav/logout are already present): T055 + three T054 groups (duration, aspect ratio, voice — voice cards play T042's preview sample), "Generate Script" → `POST /scripts`: on submit, synchronously (before any `await`) disables the button and generates one UUID `idempotencyKey` held in component state for that attempt — reused only if the client auto-retries this same attempt after a network error, never regenerated for the same logical submission (double-click protection, matches T041's atomic claim) (FR-005, FR-006); verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T054, T055, T032, T033d
- [X] T057 [P] [US1] `frontend/components/studio/word-counter.tsx` — live word-counter badge; disables "Approve & Create Video" once over the target (FR-010)
- [X] T058 [US1] `frontend/app/(app)/review/page.tsx` — Review screen: corrected idea, editable RTL Urdu script (Noto Nastaliq Urdu), editable scene list, T057, "Regenerate" (same pattern as T056's Create page: synchronously disables the button and generates one UUID `idempotencyKey` per logical regenerate attempt before calling `POST /scripts` — double-click protection, matches T041's atomic claim) and "Approve & Create Video" (same pattern: synchronously disables the button and generates one UUID `idempotencyKey` before calling `POST /videos`, navigates to the progress page) (FR-009, FR-010, FR-011, FR-012); verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T057, T032
- [X] T059 [P] [US1] `frontend/components/studio/progress-stepper.tsx` — step list: Preparing / Generating scene `i/N` / Adding voice / Finalizing / Ready (design-system.md)
- [X] T060 [US1] `frontend/app/(app)/videos/[id]/progress/page.tsx` — TanStack Query `refetchInterval: 3000` against `GET /videos/{id}`; renders T059; inline player + Download on Ready; friendly failure message on Failed (FR-013, FR-014, FR-019 partial, FR-020 partial); verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T059, T032

**Checkpoint**: User Story 1 is fully functional and independently testable —
a student can go from idea to a downloadable video with zero GPU cost.

---

## Phase 4: User Story 2 - Track and manage my videos (Priority: P2)

**Goal**: "My Videos" grid with play/download/delete/retry, and the
"X of Y videos left today" indicator on the Create page.

**Independent Test**: A student with one Ready and one Failed job opens "My
Videos," manages both, and sees their remaining daily quota on the Create page.

- [X] T061 [US2] `backend/app/services/video_job_service.py` — extend with `list_for_student(student_id, cursor, limit)`, `delete(job_id)` (only if `status` is `ready`/`failed`, else `AppError("DELETE_WHILE_PROCESSING")`), `retry(job_id)` (`AppError("RETRY_NOT_ALLOWED")` unless `failed`; otherwise creates a new job via `create_job` reusing the approved idea/script/duration/aspect-ratio/voice) (FR-019, FR-021, FR-022) — depends on T043
- [X] T062 [US2] `backend/app/api/videos.py` — extend with `GET /videos` (list, cursor-paginated), `DELETE /videos/{id}`, `POST /videos/{id}/retry` (FR-019, FR-020, FR-021, FR-022) — depends on T061, T045
- [X] T063 [P] [US2] `frontend/components/studio/usage-badge.tsx` — "X of Y videos left today" (reads `GET /me`'s `usage`); mounted into T056's Create page (FR-024) — depends on T032
- [X] T064 [P] [US2] `frontend/components/studio/video-card.tsx` — thumbnail with hover-autoplay preview, status badge, title/date/duration/aspect-ratio, play/download/delete/retry actions (FR-019, FR-020, FR-021, FR-022)
- [X] T065 [US2] `frontend/app/(app)/videos/page.tsx` — "My Videos" grid using T064, calling T062's list/delete/retry endpoints, friendly failure-reason display (FR-019, FR-021, FR-022, FR-033); verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T064, T032

**Checkpoint**: User Stories 1 + 2 both independently functional.

---

## Phase 5: User Story 3 - Reset a forgotten password (Priority: P3)

**Goal**: Self-service "Forgot password" → single-use emailed link → new password.

**Independent Test**: An existing student requests a reset, receives the
email, follows the link, sets a new password, and logs in with it.

- [X] T066 [US3] `backend/app/services/email_service.py` — `EmailSender` protocol + `ResendEmailSender` (resend.com REST API); 10s timeout + 2 retries + friendly `AppError("EMAIL_SEND_FAILED")` on exhaustion (research.md A2, FR-003)
- [X] T067 [US3] `backend/app/services/password_reset_service.py` — `create_token(student)` (invalidates any outstanding token for that student first, stores only a SHA-256 hash, 30-minute expiry), `verify_token(raw_token)`, `consume_token(raw_token, new_password)` (FR-003, FR-004) — depends on T013, T019
- [X] T068 [US3] `backend/app/schemas/auth.py` — extend with `ForgotPasswordRequest`/`ResetPasswordRequest` schemas
- [X] T069 [US3] `backend/app/api/auth.py` — extend with `POST /auth/forgot-password` (always `202`, never reveals account existence; calls T066 + T067) and `POST /auth/reset-password` (FR-003, FR-004) — depends on T067, T068, T066
- [X] T070 [US3] `backend/tests/test_auth.py` — extend with password-reset coverage: issue/consume, expired token, already-used token, superseded-by-newer-token (completes critical path #1) — depends on T069
- [X] T071 [P] [US3] `frontend/app/(auth)/forgot-password/page.tsx` — email form → `POST /auth/forgot-password`; always shows a generic "check your email" confirmation; verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T032
- [X] T072 [P] [US3] `frontend/app/(auth)/reset-password/page.tsx` — new-password form (token read from the URL query) → `POST /auth/reset-password`; friendly expired/used-link message linking back to forgot-password; verify mobile-first, no horizontal scroll at 375px width (FR-031) — depends on T032

**Checkpoint**: User Stories 1 + 2 + 3 all independently functional.

---

## Phase 6: User Story 4 - Discover the product via the public landing page (Priority: P4)

**Goal**: Premium marketing landing page with theme toggle, hero, how-it-works,
showcase, and FAQ.

**Independent Test**: An anonymous visitor views the hero/steps/showcase/FAQ,
toggles the theme (persists across reload), and clicks through to sign-up.

- [X] T073 [US4] Verify `frontend/components/layout/theme-toggle.tsx` (built in Foundational, T033b) renders and persists correctly for an anonymous visitor on the public routes — no new component; this is reuse, not creation (FR-030)
- [X] T074 [US4] `frontend/app/(public)/layout.tsx` — mounts T033c's site-header, reused as-is (it already renders the anonymous "Login"/"Start Creating" + theme-toggle variant for a visitor with no session) around every `(public)/*` route — depends on T033c
- [X] T075 [P] [US4] `frontend/components/marketing/hero.tsx` — autoplaying muted sample video, headline, "Start Creating" CTA → `/register` (FR-029)
- [X] T076 [P] [US4] `frontend/components/marketing/how-it-works.tsx` — 3-step explanation: Write idea → Review script → Get video (FR-029)
- [X] T077 [P] [US4] `frontend/components/marketing/showcase-grid.tsx` — sample-video grid, hover-autoplay (same visual language as T064's Video Card) (FR-029)
- [X] T078 [P] [US4] `frontend/components/marketing/faq-accordion.tsx` — FAQ section (shadcn `Accordion`) (FR-029)
- [X] T079 [P] [US4] `frontend/components/marketing/site-footer.tsx` — footer (FR-029)
- [X] T080 [US4] `frontend/app/(public)/page.tsx` — assembles T075–T079 inside T074's public layout; verify mobile-first responsive layout, no horizontal scroll, tokens-only styling (FR-029, FR-031, FR-032) — depends on T075, T076, T077, T078, T079, T074
- [X] T081 [P] [US4] `frontend/public/samples/` — bundled sample showcase videos/thumbnails (static marketing assets, distinct from T046's test fixtures)

**Checkpoint**: All four user stories independently functional — feature-complete in mock mode.

---

## Phase 7: Real GPU Pipeline — RunPod + ComfyUI + Wan 2.2 + OmniVoice

**Purpose**: Swap in real generation behind `VIDEO_PROVIDER=runpod`, reading
model weights from a RunPod **network volume** rather than baking them into the
GPU worker image (new item #3). This phase is independent of the mock-mode
user stories above and can be built/tested entirely separately against a real
RunPod account.

- [X] T082 [P] `gpu-worker/volume/LAYOUT.md` — documents the RunPod network volume layout: `/runpod-volume/models/wan2.2-ti2v-5b/`, `/runpod-volume/models/omnivoice-urdu-6000/`, `/runpod-volume/voices/male.wav`, `/runpod-volume/voices/female.wav`
- [X] T083 [P] `gpu-worker/scripts/download_weights.sh` — one-time, idempotent script (skips files already present) that downloads exactly these weights onto the network volume at the T082 paths:
  - `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` → `split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors`
  - `Comfy-Org/Wan_2.1_ComfyUI_repackaged` → `split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors`
  - `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` → `split_files/vae/wan2.2_vae.safetensors`
  - `mlwithabdullah/omnivoice-urdu-6000` (full repo)
- [X] T083a `gpu-worker/comfyui/extra_model_paths.yaml` — ComfyUI config pointing its `diffusion_models`/`text_encoders`/`vae` search paths at the T082 network-volume directories, so T084's workflow can reference model filenames without any absolute path baked into the workflow JSON — depends on T082, T083
- [X] T084 `gpu-worker/workflows/wan22_ti2v5b.json` — ComfyUI API-format workflow template, parameterized by prompt/resolution/frame-count, referencing the three model files from T083 by name (resolved via T083a's search paths) (research.md A4) — depends on T083a
- [X] T085 `gpu-worker/handler.py` — RunPod Serverless entrypoint: starts headless ComfyUI, submits T084 per scene (16:9→1280×704, 9:16→704×1280, 121 frames@24fps), calls `runpod.serverless.progress_update()` after each completed scene (research.md A4) — depends on T084
- [X] T086 `gpu-worker/omnivoice/infer.py` — OmniVoice Urdu single-pass narration synthesis against the chosen voice's reference file from the T082 volume (research.md A5)
- [X] T087 `gpu-worker/handler.py` — extend: after T085/T086 complete, `PUT` the raw clips + narration audio to the presigned R2 URLs supplied in the job input; every PUT has a 30s timeout + 2 retries, surfacing a job-level failure (not a crash) on exhaustion (Complexity Tracking's justified exception) — depends on T085, T086
- [X] T088 `gpu-worker/Dockerfile` — container image: ComfyUI + Python deps baked in; model weights are **not** baked in — mounted from the network volume at runtime (new item #3) — depends on T085
- [X] T089 `backend/app/services/runpod_provider.py` — backend-side client: `submit_job(scenes, resolution, frames, narration, voice_id, presigned_put_urls)` via the `runpod` SDK, polls status/progress; 30s connect timeout + 3 retries with backoff; friendly `AppError("RUNPOD_UNAVAILABLE")` on exhaustion (FR pipeline, Constitution Principle V) — depends on T025
- [X] T090 `backend/app/services/video_pipeline.py` — extend `run_job()` to branch on `VIDEO_PROVIDER`: `mock` keeps using T047 unchanged; `runpod` generates presigned PUT URLs via T025 and calls T089, then proceeds through the *same* T048 FFmpeg finalize step either way — depends on T089, T049

**Checkpoint**: Setting `VIDEO_PROVIDER=runpod` with real credentials produces
real generated videos through the identical API/DB/UI surface used in mock mode.

---

## Phase 9: Revision 2026-11-07 — Per-scene narration sync + attachment download

**Purpose**: Narration must describe what each scene shows (spec FR-007/FR-009/FR-010/FR-017,
plan.md "Design Revision 2026-11-07"), and Download must save a file instead of expanding the
player (FR-020). Spec/plan/contract/data-model updated first.

- [X] T096 Spec, plan, tasks, `contracts/openapi.yaml`, `data-model.md` updated for per-scene `{visualPrompt, narrationUr}` and `GET /videos/{id}/download`
- [X] T097 `backend/app/services/llm_service.py` + `schemas/scripts.py` + `api/scripts.py` — structured output `scenes[]={visual_prompt, narration_ur}`; per-scene `WORDS_PER_5S_MAX`; per-scene retry-with-feedback + sentence-boundary trim; Roman-Urdu checks on idea and narrations; joined `urdu_script`
- [X] T098 `backend/app/schemas/videos.py`, `services/video_job_service.py`, `models/video_job.py` — scene objects in the job payload; server-derived `urdu_script`; per-scene validation; legacy string rows normalised (no migration, JSONB)
- [X] T099 `gpu-worker/handler.py` + `backend/app/services/runpod_provider.py` — per-scene OmniVoice synthesis, `narrations[]` PUT URLs, `narration_durations_seconds[]` output (**worker image rebuild required**)
- [X] T099a `backend/app/services/ffmpeg_service.py` + `video_pipeline._finalize` + `mock_provider` — per-scene fit (atempo ≤ `MAX_NARRATION_SPEEDUP`, silence pad to 5 s) and concat; mock follows the same path
- [X] T099b `frontend` Review page — per-scene cards (visual prompt + RTL editable narration + per-scene word counter); Approve disabled if any scene is over limit/empty
- [X] T100 Download root cause confirmed by Playwright reproduction (cross-origin `<a download>` ignored → navigation to raw MP4), then `GET /videos/{id}/download` (R2 `ResponseContentDisposition`, SigV4; local HMAC-signed `/downloads/local`), shared `DownloadButton` on the progress page and My Videos card
- [X] T101 Tests: updated the existing tests that break (scene shape, `_finalize`, runpod payload) + Playwright `frontend/e2e/download.spec.ts` (real download event, `.mp4` saved, player size unchanged)

---

## Phase 8: Production Deployment (Final Phase)

**Purpose**: Ship the whole stack onto the existing shared cPanel/WHM VPS (AlmaLinux 8, rootful Podman 4.9, Apache EA4 + AutoSSL) without disturbing its 12 live sites or the other projects' podman containers. Caddy is dropped — see plan.md "Design Revision 2026-11-12".

- [X] T091 [P] `backend/Dockerfile` + `backend/.dockerignore` — production image (multi-stage, non-root uid 10001); `ffmpeg` in the final stage since the **same image** runs the API, `worker` and `scheduler`; uvicorn `--proxy-headers` with `FORWARDED_ALLOW_IPS=*` (port reachable only via 127.0.0.1 / the private network)
- [X] T091a Production-only app changes: `COOKIE_SECURE` setting (default true) used by the session + CSRF cookies; `FFMPEG_THREADS` (default 2) caps ffmpeg decoder/filter/encoder threads in `ffmpeg_service._run` (test extended in `tests/test_pipeline_hardening.py`)
- [X] T092 [P] `frontend/Dockerfile` + `frontend/.dockerignore` + `next.config.ts` `output: "standalone"` — non-root; `NEXT_PUBLIC_API_BASE_URL=/api` and `BACKEND_ORIGIN=http://backend:8000` are build args (both baked at build time), so the `/api` rewrite works as the SSH-tunnel fallback; `.env.local` excluded from the build context
- [X] T093 `infra/docker-compose.prod.yml` — `frontend` (127.0.0.1:3100), `backend` (127.0.0.1:8100), `worker`, `scheduler`, `postgres:16`, `redis:7` (no published ports); everything named `uvs-*` (`name: uvs`, `uvs-pgdata`, `uvs-redis`, `uvs-net`); `restart: always`; `depends_on: service_healthy`; `CMD-SHELL` healthchecks (podman 4.9 compat API re-splits exec-form args); measured memory caps totalling 1280 MB (worker 624, scheduler 80) with swap disabled per container; Redis `maxmemory 32mb noeviction`; worker under `nice -n 10`; json-file logs capped at 10 MB — depends on T091, T092
- [X] T093a `infra/uvs.sh` → `/opt/uvs/uvs` — the only way compose is run on the VPS: pins project `uvs`, the compose file, the current image tag and `DOCKER_HOST=unix:///run/podman/podman.sock`
- [X] T093c `backend/app/services/video_job_service.py` — import `llm_service` lazily inside `create_job` so the scheduler no longer loads the OpenAI Agents SDK (scheduler peak 116 → 60 MB; cap 144 → 80 MB, freed memory moved to the worker)
- [X] T093d `infra/release.sh` post-deploy check — every `uvs-*` container must exist and have restart policy `always`, and `podman-restart.service` must be enabled (reboot safety verified without rebooting the live server)
- [X] T093b Compose-tool decision verified on AlmaLinux 8.10 + podman 4.9.4: Docker Compose v5.7.1 over `podman.socket` chosen; EPEL podman-compose 1.0.6 rejected (no health-gated `depends_on`, broken exec-form healthchecks, `memswap_limit` ignored)
- [X] T094 `infra/apache/urdu-video-studio.conf` — cPanel EA4 userdata include for `std` and `ssl`: `/.well-known/` excluded, `/api/` → `127.0.0.1:8100/` (prefix stripped, like the dev rewrite — also covers `/api/static` and `/api/downloads/local`), `/` → `127.0.0.1:3100`, `ProxyPreserveHost`, `X-Forwarded-Proto`, timeouts; README gives the `httpd -M` check, `/scripts/rebuildhttpdconf`, `/scripts/restartsrv_httpd`
- [X] T095 `README.md` — "Deploy" (beginner, one command per step: SSH key → tools → first deploy → SSH-tunnel test → first login; updates; rollback; backups) and a separate "When the domain is ready" (cPanel account, DNS, AutoSSL, Apache include) section — depends on T093, T094
- [X] T095a `infra/deploy.sh` (+ `infra/deploy.env.example`, real `infra/deploy.env` gitignored) — runs on WSL: refuses a dirty tree, builds both images tagged with the git short SHA, streams them with `docker save | gzip | ssh … podman load` (re-tags instead when the VPS already has that image ID), uploads compose + wrapper, runs `alembic upgrade head`, restarts, prints a health check, fails loudly; `deploy.sh rollback` re-points to the previous tag
- [X] T095b `infra/.env.production.example` — every production variable documented; the real `/opt/uvs/.env` exists only on the VPS, `chmod 600`
- [X] T095c `infra/backup/uvs-backup.sh` — daily `pg_dump -Fc` via root cron into `/opt/uvs/backups`, 7-day retention

**Checkpoint**: Feature is deployable to production exactly as specified by the constitution.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup — **blocks all user stories**.
- **User Story 1 (Phase 3)**: depends on Foundational only.
- **User Story 2 (Phase 4)**: depends on Foundational + US1's `video_job_service`/`videos` API existing (T043, T045) to extend.
- **User Story 3 (Phase 5)**: depends on Foundational only (independent of US1/US2 — could be built in parallel with them by a second developer).
- **User Story 4 (Phase 6)**: depends on Foundational's theme-provider/site-header (T033, T033b, T033c); it *reuses* the Foundational header rather than building its own (T073/T074 are reuse/wrapper tasks, not new components). Its showcase grid visually mirrors US2's Video Card (T064) but does not import it.
- **Real GPU Pipeline (Phase 7)**: depends on US1's `video_pipeline.py`/`storage_r2.py` (T049, T025) existing to extend — otherwise independent of US2–US4.
- **Production Deployment (Phase 8)**: depends on every prior phase being functionally complete.

### Story Independence

- US1 has no dependency on US2/US3/US4 — it is the MVP.
- US2 extends files US1 created (`video_job_service.py`, `videos.py`) but adds no new capability US1 depends on — US1 remains fully testable without US2.
- US3 (password reset) only touches `auth.py`/`sessions`-adjacent code — fully independent of US1/US2/US4; could be built by a second developer in parallel with US1.
- US4 (landing page) only touches `frontend/components/marketing/*` and the shared layout — fully independent of US1/US2/US3.

### Parallel Opportunities

- All Setup tasks marked `[P]` (T002–T008) run in parallel once T001 exists.
- Within Foundational: the four model files (T011–T014) in parallel; `storage_local.py`/`storage_r2.py` (T024/T025) in parallel once T023 exists; T031a (Next.js rewrites) can proceed in parallel with backend T009–T031 since it only touches `frontend/next.config.ts`; T033a (design tokens) can start as soon as T003 exists, in parallel with all backend Foundational work, but T033b→T033c→T033d are sequential (each builds on the previous).
- Within US1: T038 (moderation) and T040 (schemas) in parallel; T046 (mock assets) in parallel with T042 (voices endpoint); frontend T054/T055/T057/T059 in parallel with each other and with backend tasks.
- Within US4: T075, T076, T077, T078, T079, T081 are all `[P]` — a full landing page can be built by one person in an afternoon by parallelizing every section (T073/T074 are lightweight reuse/verification steps, not new build work).
- Within Phase 7: T082 (volume layout doc) and T083 (weight download script) in parallel; T083a (extra_model_paths.yaml) needs both to exist first.
- **US2, US3, and US4 can be staffed to three different developers simultaneously** once Foundational is done, each working from Phase 3's artifacts without blocking one another.
- Phase 7 (Real GPU Pipeline) can start as soon as US1's `video_pipeline.py`/`storage_r2.py` exist — it does not need US2/US3/US4 complete.

---

## Parallel Example: User Story 1

```bash
# Backend, independent files, launch together:
Task: "backend/app/services/moderation_service.py"
Task: "backend/app/schemas/scripts.py"
Task: "backend/app/services/mock_provider/assets/"
Task: "backend/app/api/voices.py"

# Frontend, independent components, launch together:
Task: "frontend/components/studio/option-card.tsx"
Task: "frontend/components/studio/idea-textarea.tsx"
Task: "frontend/components/studio/word-counter.tsx"
Task: "frontend/components/studio/progress-stepper.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 (Foundational).
2. Complete Phase 3 (User Story 1, mock mode).
3. **STOP and VALIDATE**: run `specs/001-video-generation/quickstart.md`'s walkthrough end-to-end — register, create, approve, watch progress, play/download. Zero GPU spend.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. Add US1 → validate independently → demoable MVP (mock mode, $0 GPU cost).
3. Add US2 → validate independently → students can manage their history.
4. Add US3 → validate independently → self-service account recovery.
5. Add US4 → validate independently → public-facing funnel.
6. Add Phase 7 (Real GPU Pipeline) → switch `VIDEO_PROVIDER=runpod` in a staging environment → validate a real generated video end-to-end.
7. Add Phase 8 (Production Deployment) → ship.

### Parallel Team Strategy

With multiple developers, once Foundational (Phase 2) is done:
- Developer A: User Story 1 (critical path — unblocks the rest of the demo).
- Developer B: User Story 3 (password reset) — fully independent of A.
- Developer C: User Story 4 (landing page) — fully independent of A and B.
- Once US1 lands, Developer D can start User Story 2 (extends US1's files) while a fifth developer starts Phase 7 (GPU pipeline) against US1's `video_pipeline.py` seam.

---

## Notes

- `[P]` tasks touch different files with no dependency on an incomplete task.
- `[Story]` labels map tasks to US1–US4 for traceability; Setup/Foundational/GPU/Deploy carry no story label by design.
- Every external-service call (OpenAI moderation + Agents SDK, Resend, R2, RunPod, `ffmpeg`, Redis, Postgres) has its timeout/retry/friendly-error behavior stated inline in the owning task, per Constitution Principle V.
- Tests are limited to the three constitution-mandated critical paths (T031/T070 auth incl. password reset, T052 job state machine, T053 LLM output parsing) — no other test files are planned.
- **No hard-coded colors anywhere outside `frontend/app/globals.css`** (T033a) — every component/page task from Phase 2 onward styles exclusively via its CSS variables/utility classes (`.urdu` included).
- **Navigation/logout exist from Phase 2 onward**: T033b–T033d build the shared header once in Foundational; US4 (T073/T074) reuses it rather than rebuilding it.
- **Same-origin API**: T031a's Next.js rewrite + T094's Apache routing mean the browser only ever calls its own origin's `/api/*` — session and CSRF cookies are first-party in both dev and prod, and the backend's CORS config (T026) never needs to support cross-origin credentials.
- **`ffmpeg` is required wherever the backend image runs**: T091's Dockerfile installs it once and `worker`/`scheduler` (T093) share that same image, and the quickstart's local-dev prerequisites list it too.
- Commit after each task or logical group; stop at any phase checkpoint to validate that story independently before continuing.
