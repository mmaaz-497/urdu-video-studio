---
id: 0002
title: Align spec with constitution v2.0.0
stage: spec
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: general (manual spec revision, no slash command)
labels: ["spec", "video-generation", "breaking-change", "roles", "password-reset", "duration"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/spec.md
 - specs/001-video-generation/checklists/requirements.md
tests:
 - none (specification document; no automated tests applicable)
---

## Prompt

Update specs/001-video-generation/spec.md to match the amended constitution, keep everything else as is, and re-run the quality checklist:

1. Remove the Admin role, the admin panel user story (User Story 3), and all admin-related requirements, entities and edge cases. Renumber stories/requirements cleanly.
2. Daily video and script limits come from server configuration (DAILY_VIDEO_LIMIT, DAILY_SCRIPT_LIMIT), same for every student; keep "X of Y videos left today" and the midnight Asia/Karachi reset.
3. Duration: on the Create page the student picks 5s, 10s or 15s (visual options, like aspect ratio). The system generates exactly 1, 2 or 3 scenes to match, and the progress view counts scenes accordingly (e.g. 1/2, 2/2).
4. Narration length must fit the chosen duration (roughly 13–15 Urdu words per 5 seconds). The Review screen shows a live word counter and blocks approval if the script is too long for the chosen duration.
5. The final video MUST NEVER exceed the chosen duration (max 15s). If the voice is slightly longer than the video, the voice may be sped up by at most 10%; if it still does not fit, the job fails with a friendly reason ("Script is too long for the chosen duration — please shorten it") and does not count toward the daily limit.
6. Add self-service password reset: "Forgot password" sends a time-limited, single-use reset link by email; the student sets a new password. Email verification at signup stays out of scope.

## Response snapshot

Rewrote `specs/001-video-generation/spec.md` in place to align with constitution v2.0.0:

- **Removed**: Admin role (FR-003/004 old), the admin panel user story (old US3) and its 5 acceptance scenarios, the admin-disables-account edge case, the "Admin Panel" FR group (old FR-028/029/030), the Admin and Daily-Limit-Setting key entities, and all "admin-configured"/"admin-set" wording throughout (daily limits, error-handling FR, success criteria, assumptions).
- **Renumbered**: 4 user stories (P1 Create, P2 My Videos, P3 Reset a forgotten password [new], P4 Landing page [was P4, unchanged position today since old US3 Admin was removed and the new Password Reset story was inserted ahead of Landing page]); 34 functional requirements (down from 36), cleanly sequential FR-001..FR-034 across the same thematic groups minus "Admin Panel" plus a new password-reset block under "Accounts & Authentication".
- **Daily limits**: FR-023/FR-027 now source values from server configuration (`DAILY_VIDEO_LIMIT`, `DAILY_SCRIPT_LIMIT`) applied identically to every student; "X of Y left today" and midnight Asia/Karachi reset retained unchanged (FR-024/FR-025).
- **Duration selection**: FR-006 adds duration (5/10/15s) as a third visual-card choice alongside aspect ratio and voice; FR-007 ties scene count (1/2/3) and narration word target (~13–15 Urdu words per 5s segment) to the chosen duration; FR-013 progress counter generalized to 1/N..N/N; FR-018 final video length MUST equal the chosen duration and MUST NEVER exceed 15s.
- **Word-counter approval gate**: new FR-009 (live counter on Review screen) and FR-010 (disables "Approve & Create Video" while over target) — net-new requirements, not in the prior version.
- **Narration-fit fallback rewritten**: replaced the old "last scene holds/freezes" behavior with new FR-017 — speed up voice by at most 10%, and if still too long, fail the job with the exact friendly reason "Script is too long for the chosen duration — please shorten it," explicitly not counted toward the daily video limit. Updated the corresponding edge case and SC-003 to match.
- **Password reset**: new User Story 3 (P3) with 4 acceptance scenarios, new FR-003/FR-004 under "Accounts & Authentication", a new "Password Reset Token" key entity, 2 new edge cases (expired/reused link; superseded-by-newer-link), and a new SC-007. Removed the old assumption that said password reset was out of scope.
- **Out of Scope**: added "Email verification at signup" and "Any admin role, admin panel, or per-student daily-limit overrides" as explicit exclusions (per instruction #6 and the constitution's role removal).
- **Assumptions**: removed the obsolete admin-provisioning and "password reset not covered" assumptions; added assumptions that the two daily limits are global server config with no per-student override path, and that password-reset email rides on the constitution's transactional email service.

Re-ran the quality checklist at `specs/001-video-generation/checklists/requirements.md` against the revised spec: all 18 items still pass (no [NEEDS CLARIFICATION] markers introduced, success criteria remain measurable and tech-agnostic, scope and assumptions stay current). Appended a dated re-validation note to the checklist's Notes section documenting what changed and confirming no iteration was needed.

## Outcome

- ✅ Impact: `specs/001-video-generation/spec.md` is now consistent with constitution v2.0.0 (single student role, env-config-driven daily limits, flexible-but-capped video duration, mandatory password reset). The spec is unblocked for `/sp.plan`.
- 🧪 Tests: none (specification artifact)
- 📁 Files: `specs/001-video-generation/spec.md` (rewritten), `specs/001-video-generation/checklists/requirements.md` (re-validated, note appended)
- 🔁 Next prompts: `/sp.plan` to produce the technical plan — will need to reflect duration-dependent scene counts, the word-counter mechanism, the 10%-speedup/fail fallback, and the transactional email integration for password reset.
- 🧠 Reflection: The six numbered instructions mapped cleanly onto distinct, non-overlapping edits (roles, limits sourcing, duration/scenes, word counter, narration-fit fallback, password reset), so the rewrite could be done as one pass without needing clarification; the trickiest part was ensuring every old "15-second-only" and "admin" reference was hunted down consistently (FRs, edge cases, entities, success criteria, assumptions, out-of-scope) rather than just the obviously-named sections.

## Evaluation notes (flywheel)

- Failure modes observed: none — single-pass rewrite, re-validated checklist stayed at 18/18 pass.
- Graders run and results (PASS/FAIL): checklist re-validation — PASS (18/18); grep-equivalent manual scan for leftover "admin"/"15-second" (as a fixed-only constraint)/"last scene holds" phrasing — PASS (none found in the new text).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
