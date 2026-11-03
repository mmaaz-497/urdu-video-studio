---
id: 0001
title: Student video generation feature spec
stage: spec
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: /sp.specify
labels: ["spec", "video-generation", "student-flow", "admin-panel"]
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

Urdu Video Studio — students turn their idea into a 15-second video with Urdu narration.

## Who uses it
- Student: signs up, creates videos, sees their own history.
- Admin: manages students and sets daily video limits.

## Main student flow
1. Student signs up / logs in with email + password.
2. On the Create page, student types their idea in Roman Urdu or Urdu (spelling mistakes allowed), 10–500 characters.
3. Student picks aspect ratio (16:9 landscape or 9:16 vertical, shown as visual cards) and voice (Male or Female, each with a short preview sample).
4. Student clicks "Generate Script". The system:
   - corrects spelling/grammar of the idea,
   - writes an Urdu narration script that fits 15 seconds when spoken (about 35–45 words),
   - writes 3 scene descriptions (one per 5-second clip).
5. Student sees a Review screen: corrected idea, Urdu script (right-to-left, editable), and the 3 scenes (editable). Student can edit, regenerate, or approve. Nothing expensive starts before approval.
6. After "Approve & Create Video", a progress view shows clear steps: Preparing → Generating scenes (1/3, 2/3, 3/3) → Adding voice → Finalizing → Ready. Student can leave the page and come back; progress continues.
7. When ready: student can play, download (MP4), and see it in "My Videos".

## My Videos
- Grid of the student's videos with thumbnail, title (from idea), date, aspect ratio, and status badge (Processing / Ready / Failed).
- Ready videos: play, download, delete. Failed videos: show a friendly reason and a "Try again" button.

## Limits
- Each student has a daily video limit (default set by admin; admin can override per student).
- Create page shows "X of Y videos left today". When the limit is reached, generation is blocked with a friendly message showing when it resets (midnight, Asia/Karachi).
- Failed videos do NOT count toward the daily limit. Script generation (before approval) has its own reasonable limit to prevent abuse (e.g. 20 per day).

## Admin panel
- List/search students: name, email, signup date, videos today / total, status.
- Set the default daily limit for all students and override it per student.
- Disable / re-enable a student account.
- View all video jobs with status, and the failure reason for failed jobs.

## Public pages
- Premium landing page: hero with an autoplaying sample video, short headline and "Start Creating" button, "How it works" in 3 steps (Write idea → Review script → Get video), a showcase grid of sample videos, FAQ, and footer.
- Light and dark mode toggle on every page (remembers choice, defaults to system setting). Fully responsive, mobile-first.

## Safety & errors
- Ideas with unsafe or inappropriate content (violence, adult, hate, self-harm) are rejected with a polite message; no video is made.
- Every failure shows a friendly English message (never technical errors). A video job always ends as Ready or Failed — never stuck. Jobs that take too long are marked Failed with a reason.
- If the narration is longer than the video, the last scene holds so the voice is never cut off.

## Out of scope (for now)
- Payments, public sharing/social feed, video timeline editing, custom voice cloning, narration in languages other than Urdu, longer than 15-second videos.

## Success criteria
- A new student can sign up and get their first video without help.
- 95% of approved jobs finish as Ready; every job ends as Ready or Failed.
- The review screen always shows a script that fits 15 seconds.
- The daily limit can never be bypassed.

## Response snapshot

Created branch `001-video-generation` via `create-new-feature.sh` (feature 001, no prior numbered branches/specs existed) and wrote `specs/001-video-generation/spec.md` using the spec template structure:

- **4 prioritized user stories**: P1 Create a video from an idea (core MVP flow: idea → script generation → review/edit → approval gate → progress → play/download), P2 Track and manage my videos (My Videos grid, play/download/delete, retry, remaining-quota display), P3 Admin oversight (search/list students, limit management, enable/disable, platform-wide job view), P4 Public landing page discovery.
- **Edge cases**: length validation, unsafe-content rejection, both daily limits (video vs. script-generation), failed-job timeout handling, narration-overrun scene hold, double-submit protection, delete-while-processing guard, disabled-account-with-active-job behavior.
- **36 functional requirements (FR-001..FR-036)** grouped under Accounts & Roles, Create & Review Flow, Video Job Processing & Status, My Videos, Daily Limits, Admin Panel, Public Pages & UI, Error Handling.
- **Key Entities**: Student, Admin, Video Job, Scene, Daily Limit Setting, Usage Counter.
- **6 measurable Success Criteria (SC-001..006)**: the 4 given verbatim by the user plus two added (time-to-review, mobile usability) for stronger testability.
- **Assumptions section** (added, optional) documenting reasonable defaults for gaps not covered by the brief: no email verification at signup, out-of-band admin provisioning, password reset deferred to a future feature, title derivation from corrected idea, no automatic video expiry, unsafe/failed attempts still consume the script-generation quota.
- **Out of Scope section** transcribing the user's exclusions verbatim.

No `[NEEDS CLARIFICATION]` markers were used — the source brief was thorough enough (explicit limits, timezone, failure semantics, roles, exclusions) that every remaining gap had a reasonable, now-documented default.

Generated `specs/001-video-generation/checklists/requirements.md` and validated all items on the first pass — all checked, no iteration needed.

## Outcome

- ✅ Impact: First feature spec for the project is ready for `/sp.clarify` (optional, likely skippable given the all-pass checklist) or directly `/sp.plan`.
- 🧪 Tests: none (specification artifact)
- 📁 Files: `specs/001-video-generation/spec.md` (created), `specs/001-video-generation/checklists/requirements.md` (created)
- 🔁 Next prompts: `/sp.plan` to produce the technical plan against the fixed stack in the constitution; optionally `/sp.checklist` for a deeper domain-specific checklist (e.g., safety/moderation) before planning.
- 🧠 Reflection: Because the constitution (fixed stack, cost rules, error-handling mandates) was already ratified, this spec stayed strictly behavioral/technology-agnostic as required, deferring all "how" decisions (OpenAI Agents SDK, ComfyUI, FFmpeg, R2, etc.) to the plan stage.

## Evaluation notes (flywheel)

- Failure modes observed: none — spec passed the quality checklist on the first validation pass.
- Graders run and results (PASS/FAIL): requirements.md checklist — PASS (18/18 items); placeholder scan — PASS (no unresolved `[NEEDS CLARIFICATION]` or bracket tokens).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
