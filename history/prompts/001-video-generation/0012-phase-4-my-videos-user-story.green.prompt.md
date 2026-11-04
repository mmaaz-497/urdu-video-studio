---
id: 0012
title: Phase 4 My Videos user story
stage: green
date: 2026-11-03
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: Maaz
command: /sp.implement
labels: ["backend", "frontend", "video-jobs", "my-videos", "usage-limits"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - backend/app/services/video_job_service.py
 - backend/app/api/videos.py
 - backend/app/schemas/videos.py
 - frontend/lib/types.ts
 - frontend/lib/use-usage.ts
 - frontend/components/studio/usage-badge.tsx
 - frontend/components/studio/video-card.tsx
 - frontend/app/(app)/videos/page.tsx
 - frontend/app/(app)/create/page.tsx
 - frontend/app/(app)/review/page.tsx
 - specs/001-video-generation/tasks.md
tests:
 - backend/tests (pytest, 26 passed — existing suite, no new test tasks per constitution scope)
 - frontend npm run build (passed)
 - frontend npm run lint (passed)
 - manual Playwright pass against live dev servers (register, create 2 mock videos, list, delete w/ confirm, usage badge, daily-limit block state, dark/light/375px screenshots)
---

## Prompt

Implement Phase 4 (User Story 2 - My Videos, T061–T065) from specs/001-video-generation/tasks.md.

Backend:
- Extend video_job_service: list_for_student (cursor-paginated), delete (only if ready/failed, else friendly error), retry (only if failed — creates a new job reusing the same approved idea/script/duration/aspect ratio/voice, counts toward the daily limit).
- Extend videos API: GET /videos (list), DELETE /videos/{id}, POST /videos/{id}/retry.

Frontend (follow design-system.md, premium, dark + light, tokens only):
- usage-badge: "X of Y videos left today" (from GET /me), mounted on the Create page; block "Generate"/"Approve" with a friendly message when the limit is reached, showing the midnight Asia/Karachi reset.
- video-card: thumbnail with hover-autoplay preview, status badge (Processing/Ready/Failed), title/date/duration/aspect-ratio, and actions (play, download, delete, retry). Failed cards show the friendly reason.
- My Videos page: responsive grid (1→2→3→4 columns), the student's own videos only, newest first, using the list/delete/retry endpoints. Delete asks for confirmation. Verify mobile-first, no horizontal scroll at 375px.

All errors via the Toaster, friendly English only.

After coding: run pytest, npm run build, npm run lint — fix everything. Then a Playwright pass: create 2 videos (mock), open My Videos, confirm both show with correct badges, delete one, and confirm the usage badge decremented correctly and a reached-limit state shows the friendly message. Screenshot My Videos in dark + light + 375px.

Mark completed tasks [X]. Report: files created, test/build/lint results, and where screenshots are saved.

## Response snapshot

Extended `video_job_service.py` with cursor-paginated `list_for_student` (opaque base64 `created_at|id` cursor), `delete` (raises `DELETE_WHILE_PROCESSING` AppError unless terminal), and `retry` (raises `RETRY_NOT_ALLOWED` unless failed; re-submits via `create_job` under a fresh idempotency key, so it counts toward the daily limit). Added `VideoJobListItem`/`VideoJobListResponse` schemas and wired `GET /videos`, `DELETE /videos/{id}` (best-effort storage cleanup of video/thumbnail keys), and `POST /videos/{id}/retry` (enqueues the new job) into `videos.py`, sharing an `_get_owned_job` ownership-check helper with the existing `GET /videos/{id}`.

On the frontend, added a shared `useUsage()` hook (`GET /me`) backing a new `UsageBadge` pill component mounted on the Create page header, plus friendly limit-reached banners (with the Asia/Karachi reset time) on both Create and Review that disable Generate/Approve. Built `VideoCard` (status-badge-colored border, hover-autoplay `<video>` for Ready jobs, play/download/delete/retry actions gated by status, two-click inline delete confirmation) and a `/videos` "My Videos" page using `useInfiniteQuery` against the cursor-paginated list endpoint with delete/retry mutations that invalidate both the videos and usage queries.

Verification: `pytest` (26 passed, including the existing retry/delete-shaped state-machine tests), `ruff check` (clean after auto-fixing one import-order issue), `npm run build` and `npm run lint` (clean). Hit and resolved two environment issues along the way: a leaked idle-in-transaction Postgres connection from an earlier timed-out background pytest run was holding a table lock across all later DB access (terminated via `pg_terminate_backend`), and a stale duplicate `next dev` process was squatting port 3000 serving a corrupted build (killed; the fresh dev server came up on 3001). Drove a full Playwright pass against the live dev stack (register → create 2 mock videos → poll to `ready` → screenshot My Videos light/dark → delete one with the two-click confirm, verifying the toast and usage badge stay numerically correct, since FR-021/FR-026 mean deleting a Ready job does not refund the daily quota → create filler videos up to `DAILY_VIDEO_LIMIT` and confirm the Create page's friendly block banner and disabled Generate button → 375px screenshot with a scrollWidth/clientWidth check confirming no horizontal overflow). Test data cleaned up afterward. Marked T061–T065 `[X]` in tasks.md.

## Outcome

- ✅ Impact: User Story 2 (My Videos) is fully implemented end-to-end — list/delete/retry on the backend, and the usage badge + video card + My Videos grid on the frontend — and verified live, not just via unit tests.
- 🧪 Tests: pytest 26/26 passed; ruff clean; npm run build clean; npm run lint clean; manual Playwright pass covered create→list→delete→usage-consistency→limit-reached→responsive, screenshots saved under the session scratchpad.
- 📁 Files: see `files:` above — 3 backend files extended, 5 frontend files added, 2 frontend pages edited, tasks.md updated.
- 🔁 Next prompts: Phase 5 (User Story 3 — password reset, T066–T070).
- 🧠 Reflection: deleting a Ready/Failed video intentionally does not restore the day's quota (only Failed jobs are excluded from the count, per FR-026) — worth calling out explicitly since the original ask's phrasing ("confirm the usage badge decremented") could be misread as "delete refunds a slot."

## Evaluation notes (flywheel)

- Failure modes observed: a backgrounded pytest run that got silently moved to a background task by the harness left an open DB transaction holding a lock on `video_jobs`, which then blocked every other DB-touching process (the running RQ worker/scheduler, subsequent test runs) until manually detected via `pg_stat_activity` and terminated.
- Graders run and results (PASS/FAIL): pytest PASS (26/26), ruff PASS, npm build PASS, npm lint PASS, manual Playwright scenario PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): when a long-running test command gets auto-backgrounded by the harness, proactively check `pg_stat_activity` for stuck/idle-in-transaction sessions before re-running it, rather than discovering the hang after a timeout.
