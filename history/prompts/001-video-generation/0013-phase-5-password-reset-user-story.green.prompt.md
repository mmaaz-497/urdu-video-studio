---
id: 0013
title: Phase 5 password reset user story
stage: green
date: 2026-11-04
surface: agent
model: claude-sonnet-5-5
feature: 001-video-generation
branch: 001-video-generation
user: Maaz
command: /sp.implement
labels: ["backend", "frontend", "auth", "password-reset", "email"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - backend/app/services/email_service.py
 - backend/app/services/password_reset_service.py
 - backend/app/schemas/auth.py
 - backend/app/api/auth.py
 - backend/app/core/config.py
 - backend/.env.example
 - backend/tests/test_auth.py
 - frontend/app/(auth)/forgot-password/page.tsx
 - frontend/app/(auth)/reset-password/page.tsx
 - frontend/app/(auth)/login/page.tsx
 - specs/001-video-generation/tasks.md
tests:
 - backend pytest (33 passed; 7 new password-reset tests)
 - frontend npm run build (passed)
 - frontend npm run lint (passed)
 - Playwright e2e reset flow at 375px (passed)
---

## Prompt

/sp.implement Implement Phase 5 (User Story 3 - password reset, T066–T072) from specs/001-video-generation/tasks.md.

- email_service: EmailSender protocol + ResendEmailSender (10s timeout, 2 retries, friendly EMAIL_SEND_FAILED on exhaustion). If RESEND_API_KEY is empty (dev), fall back to a console/log email sender that prints the reset link to the backend log instead of sending — so the flow is fully testable locally with no email account. Make this fallback explicit and logged.
- password_reset_service: create_token (invalidate any outstanding token first, store only a SHA-256 hash, 30-min expiry), verify_token, consume_token (sets new password, single-use).
- auth API: POST /auth/forgot-password (always 202, never reveals whether the account exists), POST /auth/reset-password.
- Extend test_auth.py with reset coverage: issue/consume, expired token, already-used token, superseded-by-newer-token.
- Frontend: forgot-password page (email form → generic "check your email" confirmation) and reset-password page (new-password form, token from URL query, friendly expired/used-link message linking back). Follow design-system.md, match the login/register styling. Verify 375px, no horizontal scroll.

After coding: pytest, npm run build, npm run lint — fix everything. Playwright: request a reset for a registered student, grab the reset link from the backend log (dev console sender), open it, set a new password, confirm login works with the new password and fails with the old one. Screenshot forgot + reset pages (dark/light).

Mark completed tasks [X]. Report: files created, test/build/lint results, and confirm the full reset flow worked end-to-end.

## Response snapshot

Added `email_service.py` (async `EmailSender` protocol, `ResendEmailSender` via httpx with 10s timeout and 2 retries on network/5xx/429, `ConsoleEmailSender` dev fallback chosen when `RESEND_API_KEY` is empty and logged as such), `password_reset_service.py` (create/verify/consume; SHA-256 hash only; 30-min expiry; prior outstanding tokens invalidated; row-locked single-use consume), schemas, and `/auth/forgot-password` (202 always; email sent via BackgroundTasks so failures and timing don't leak account existence) and `/auth/reset-password`. New `FRONTEND_BASE_URL` setting builds the link. Frontend: forgot-password and reset-password pages (confirm-password field, invalid/expired/used link card), plus a "Forgot password?" link on login.

## Outcome

- ✅ Impact: US3 password reset implemented and verified end-to-end (link taken from the backend log; old password 401, new 200; reused link shows friendly message; no horizontal overflow at 375px).
- 🧪 Tests: pytest 33/33; build and lint clean.
- 📁 Files: see `files:` above.
- 🔁 Next prompts: Phase 6.
- 🧠 Reflection: forgot-password swallows EMAIL_SEND_FAILED (logs it) to preserve non-enumeration; existing sessions are not revoked on reset.

## Evaluation notes (flywheel)

- Failure modes observed: `ruff --fix`/`black` run repo-wide touched unrelated files (reverted); `pkill -f` killed the shell.
- Graders run and results (PASS/FAIL): pytest PASS, build PASS, lint PASS, Playwright PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): scope formatters to changed files.
