---
id: 0002
title: Remove admin role, video contract rewrite
stage: constitution
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: none
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: /sp.constitution
labels: ["constitution", "governance", "breaking-change", "roles", "video-contract"]
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

Amend the constitution (MAJOR version bump, since roles and the video contract change):

1. Remove the Admin role entirely. There is only one role: Student (self-registers, manages own account and videos).
2. Daily limits are no longer set by an admin. They come from server configuration (.env): DAILY_VIDEO_LIMIT and DAILY_SCRIPT_LIMIT, enforced server-side per student, reset at midnight Asia/Karachi.
3. Video output contract: the student chooses duration 5, 10 or 15 seconds (1, 2 or 3 clips of 5 seconds), aspect ratio 16:9 or 9:16. The final video MUST NEVER exceed 15 seconds.
4. Self-service password reset via email ("Forgot password" link with a time-limited, single-use token) using a transactional email service.

Update all affected principles and sections, the Sync Impact Report, and check dependent templates.

## Response snapshot

Amended `.specify/memory/constitution.md` from v1.0.0 to **v2.0.0** (MAJOR — backward-incompatible role and contract changes):

- **Principle IV (Fixed Technology Stack)**: added a transactional email service to the stack (password-reset delivery only); rewrote the video output contract bullet to student-selectable duration (5/10/15s, 1-3 clips) with a hard 15-second ceiling that can never be exceeded.
- **Principle V (Fail Loud, Fail Clear)**: added the transactional email service to the list of external calls requiring timeout/retry/clear-error discipline.
- **Principle VII (Minimal, Critical-Path Testing)**: expanded "authentication" critical path to explicitly include password reset.
- **Technology Stack & Environments**: replaced the admin-set-limits model with a new bullet — `DAILY_VIDEO_LIMIT` / `DAILY_SCRIPT_LIMIT` as environment configuration, server-enforced, no in-app override, reset at midnight Asia/Karachi.
- **Security, Access & UI Standards**: rewrote Authorization to a single `student` role (admin role and all admin capabilities removed); added a new Password reset bullet describing the time-limited single-use emailed token flow; updated Secrets bullet to mention the new env vars and email provider credentials.
- **Governance**: added a line requiring conflicting existing feature specs to be flagged and revisited before their next `/sp.plan`/`/sp.tasks`; added role/video-contract changes as explicit MAJOR-bump examples in the versioning policy.

Checked dependent templates: `plan-template.md`, `spec-template.md`, `tasks-template.md`, and `.claude/commands/*.md` — grepped for "admin" references; found only two unrelated/generic mentions (an example path `apps/admin` in plan-template.md and a tool name "pgAdmin" in sp.reverse-engineer.md), neither tied to the product's admin role, so no template edits were needed.

Flagged (not modified, out of scope for `/sp.constitution`): `specs/001-video-generation/spec.md` now contradicts the new constitution — it still specifies an Admin role, an admin panel user story, admin-set daily limits, and a fixed-15-second-only video contract. Documented this in the Sync Impact Report as a downstream artifact requiring the user to re-run `/sp.specify` or manually revise before proceeding to `/sp.plan` for that feature.

## Outcome

- ✅ Impact: Constitution now reflects a single-role (student-only) system, env-var-driven daily limits, a flexible-but-capped video duration contract, and a mandated self-service password-reset flow. This is a breaking governance change versus v1.0.0.
- 🧪 Tests: none (governance document)
- 📁 Files: `.specify/memory/constitution.md` (amended in place, Sync Impact Report updated)
- 🔁 Next prompts: Update `specs/001-video-generation/spec.md` (re-run `/sp.specify` or manual edit) to remove the Admin role/panel, change limit sourcing to env config, and rewrite the video-duration requirements before running `/sp.plan`.
- 🧠 Reflection: User explicitly called out MAJOR bump and named the four concrete changes, so no ambiguity in scope; the main judgment call was confirming no template files actually encode the admin role (verified via grep) rather than assuming they needed edits.

## Evaluation notes (flywheel)

- Failure modes observed: none — single-pass amendment, no unresolved placeholders.
- Graders run and results (PASS/FAIL): placeholder scan — PASS (no remaining bracket tokens); grep for stale "admin" references in templates/commands — PASS (only unrelated matches); version/date format check — PASS (2.0.0, ISO dates).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
