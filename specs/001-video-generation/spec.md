# Feature Specification: Student Video Generation

**Feature Branch**: `001-video-generation`
**Created**: 2026-11-02
**Status**: Draft
**Input**: User description: "Urdu Video Studio — students turn their idea into a video (5, 10, or 15 seconds) with Urdu narration." (full brief: single student role with self-service password reset, create flow with duration/aspect-ratio/voice selection, script review with a live word-counter approval gate, progress tracking, My Videos management, server-configured daily limits, public landing page, safety/error handling — see command input)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a video from an idea (Priority: P1) 🎯 MVP

A student signs up (or logs in), types their idea in Roman Urdu or Urdu, picks a
duration (5, 10, or 15 seconds), an aspect ratio, and a voice, generates a script,
reviews and optionally edits the corrected idea / Urdu narration / scene
descriptions (checking a live word counter against the chosen duration), approves
it, watches a clear step-by-step progress view, and ends up with a playable and
downloadable Urdu-narrated video of exactly the duration they chose.

**Why this priority**: This is the entire value proposition of the product. Without
it, nothing else matters — a student who can sign up but never gets a video has
received zero value.

**Independent Test**: A brand-new student can register, submit an idea, approve
the generated script without edits, wait for processing, and successfully play and
download a finished video — with no help from anyone else.

**Acceptance Scenarios**:

1. **Given** a logged-in student on the Create page, **When** they type an idea
   (10–500 characters, Roman Urdu or Urdu, with spelling mistakes) and pick a
   duration (5, 10, or 15 seconds), an aspect ratio, and a voice — each shown as
   visual option cards — **Then** the "Generate Script" action becomes available.
2. **Given** a valid idea and selections, **When** the student clicks "Generate
   Script", **Then** the system returns a corrected idea, a right-to-left Urdu
   narration script sized to the chosen duration (~13–15 Urdu words per 5
   seconds), and one scene description per 5 seconds of the chosen duration (1,
   2, or 3 scenes) — without starting any video/voice generation yet.
3. **Given** the Review screen, **When** the student edits the script, **Then** a
   live word counter updates against the target for the chosen duration, and the
   "Approve & Create Video" action is disabled whenever the script exceeds that
   target.
4. **Given** the Review screen, **When** the student edits the script or a scene
   and clicks regenerate, **Then** a new script/scenes are produced reflecting the
   edit (still matching the chosen duration's scene count), and nothing expensive
   (clip or voice generation) has started.
5. **Given** a script within the word-counter target, **When** the student clicks
   "Approve & Create Video", **Then** a progress view appears showing sequential
   steps (Preparing → Generating scenes 1/N, 2/N, … N/N → Adding voice →
   Finalizing → Ready, where N is 1, 2, or 3 depending on the chosen duration) and
   this job is the first point where GPU-based generation starts.
6. **Given** a job in progress, **When** the student navigates away and returns
   later (including after closing the browser), **Then** the progress view
   resumes showing the job's current real status, not a reset state.
7. **Given** a job that reaches "Ready", **When** the student opens it, **Then**
   they can play it inline and download it as an MP4 file of the duration they
   chose.

---

### User Story 2 - Track and manage my videos (Priority: P2)

A student returns to "My Videos" to see all videos they have created, check
status, watch or download completed ones, retry failed ones, delete ones they no
longer want, and see how many video generations they have left today.

**Why this priority**: Builds directly on User Story 1 — once a student can create
one video, they need a durable place to find, manage, and retry their work, and to
understand their remaining daily allowance.

**Independent Test**: Given a student with at least one prior video job (one Ready,
one Failed), opening "My Videos" shows both with correct thumbnail, title, date,
duration, aspect ratio, and status badge; the student can play/download/delete the
Ready one and see a friendly failure reason with a "Try again" button on the Failed
one.

**Acceptance Scenarios**:

1. **Given** a student with prior video jobs, **When** they open "My Videos",
   **Then** they see a grid of their own videos only, each showing thumbnail,
   title (derived from their idea), creation date, duration, aspect ratio, and a
   status badge (Processing / Ready / Failed).
2. **Given** a Ready video in the grid, **When** the student chooses play,
   download, or delete, **Then** the corresponding action completes and (for
   delete) the video no longer appears in the grid.
3. **Given** a Failed video in the grid, **When** the student views it, **Then**
   they see a friendly, non-technical failure reason and a "Try again" button
   that starts a new attempt using the same approved idea/script/duration.
4. **Given** the Create page, **When** the student has used some of their daily
   allowance, **Then** they see "X of Y videos left today" reflecting their
   current usage against the server-configured daily limit.

---

### User Story 3 - Reset a forgotten password (Priority: P3)

A student who forgot their password requests a reset from the login screen,
receives a time-limited, single-use link by email, and sets a new password to
regain access — without any manual intervention.

**Why this priority**: Important for retention (a locked-out student is a lost
student) but not required for a first-time student's first successful video.

**Independent Test**: A student with an existing account can click "Forgot
password", receive the reset email, follow the link, set a new password, and log
in with it — entirely self-service.

**Acceptance Scenarios**:

1. **Given** the login screen, **When** a student clicks "Forgot password" and
   submits their email, **Then** the system sends a time-limited, single-use
   reset link to that address if an account exists for it, without revealing
   whether the email is registered.
2. **Given** a valid, unexpired reset link, **When** the student opens it and
   submits a new password, **Then** their password is updated and the link can
   never be used again.
3. **Given** an expired or already-used reset link, **When** the student opens
   it, **Then** they see a friendly message explaining the link is no longer
   valid and offering to request a new one.
4. **Given** a student who requests a second reset link before using the first,
   **When** they later try the first link, **Then** it is rejected because only
   the newest outstanding link is valid.

---

### User Story 4 - Discover the product via the public landing page (Priority: P4)

An anonymous visitor lands on the marketing page, watches an autoplaying sample
video, reads a 3-step "how it works" explanation, browses a showcase of sample
videos, reads the FAQ, toggles light/dark mode, and proceeds to sign up.

**Why this priority**: Drives top-of-funnel signups and sets expectations, but the
product already delivers its core value (Stories 1–2) to anyone who reaches the
Create page directly; the landing page is marketing, not core functionality.

**Independent Test**: An anonymous visitor (no account) can open the public URL,
see the hero/sample video, steps, showcase, and FAQ, flip the theme toggle and have
it persist on reload, and click "Start Creating" to land on sign-up.

**Acceptance Scenarios**:

1. **Given** an anonymous visitor, **When** they load the landing page, **Then**
   they see a hero section with an autoplaying sample video, a headline, and a
   "Start Creating" call to action.
2. **Given** the landing page, **When** the visitor scrolls, **Then** they see a
   3-step "how it works" (Write idea → Review script → Get video), a showcase grid
   of sample videos, an FAQ section, and a footer.
3. **Given** any page in the app, **When** the visitor toggles light/dark mode,
   **Then** the choice is remembered on their next visit, defaulting to their
   system setting if they have never chosen.
4. **Given** the landing page on a mobile-width screen, **When** it renders,
   **Then** all sections remain usable and readable without horizontal scrolling.

---

### Edge Cases

- Idea text shorter than 10 characters or longer than 500 characters is rejected
  before script generation, with a message stating the allowed range.
- Idea text flagged as unsafe/inappropriate (violence, adult, hate, self-harm) is
  rejected with a polite, non-technical message; no script and no video are
  produced, and the attempt still counts toward the daily script-generation limit
  (it consumed an LLM call).
- Student reaches the daily **video** limit (server-configured, same for every
  student): the Create page blocks generation and shows a friendly message stating
  when the limit resets (midnight, Asia/Karachi).
- Student reaches the daily **script-generation** limit (separate, server-configured,
  higher cap): "Generate Script" / "regenerate" is blocked with a friendly message,
  independent of the video limit.
- A video job fails at any stage (scene generation, voice, or assembly): it is
  marked Failed with a human-readable reason and does **not** count toward the
  daily video limit; clicking "Try again" starts a brand-new job that **does**
  count toward the limit.
- A video job exceeds a maximum allowed processing time: it is automatically
  marked Failed with a timeout-related reason instead of remaining "Processing"
  indefinitely.
- Generated narration runs slightly longer than the chosen video duration: the
  system speeds up the voice audio by at most 10% to try to fit it. If it still
  does not fit after that adjustment, the job is marked Failed with the reason
  "Script is too long for the chosen duration — please shorten it," and this
  failure does **not** count toward the daily video limit.
- The script's live word counter is at or over the limit for the chosen duration:
  "Approve & Create Video" stays disabled until the student shortens the script
  (by editing or regenerating).
- Student double-clicks "Generate Script" or "Approve & Create Video": only one
  script generation / one video job is created per click sequence (no duplicates,
  no double-charging of limits).
- Student tries to delete a video that is still Processing: deletion is not
  available until the job reaches Ready or Failed.
- Student picks a duration, aspect ratio, and voice, and later edits the script
  without changing those selections: the original duration, aspect ratio, and
  voice remain in effect for that job, and the scene count stays matched to the
  chosen duration (1, 2, or 3 scenes).
- A password-reset link is opened after it has expired, or after it has already
  been used once: it is rejected with a friendly message offering to request a
  new link.
- A student requests a new password-reset link while an earlier one is still
  outstanding: only the newest link remains valid; the earlier one is invalidated.

## Requirements *(mandatory)*

### Functional Requirements

**Accounts & Authentication**

- **FR-001**: System MUST allow a visitor to self-register as a Student using
  email + password.
- **FR-002**: System MUST allow a registered Student to log in with email +
  password and remain in a session until they log out or the session expires.
- **FR-003**: System MUST let a Student request a password reset from the login
  screen by submitting their email; the system sends a time-limited, single-use
  reset link by email without revealing whether that email has an account.
- **FR-004**: System MUST let a Student set a new password via a valid,
  unexpired, unused reset link; the link MUST become permanently invalid
  immediately after a successful reset, after it expires, or as soon as a newer
  reset link is requested for the same account.

**Create & Review Flow**

- **FR-005**: System MUST let a Student submit an idea of 10–500 characters in
  Roman Urdu or Urdu, tolerating spelling mistakes.
- **FR-006**: System MUST let a Student choose, as visual option cards, a
  duration (5, 10, or 15 seconds), an aspect ratio (16:9 or 9:16), and a voice
  (Male or Female, each with a short preview sample) before generating a script.
- **FR-007**: System MUST, on "Generate Script", produce: a corrected version of
  the idea, an Urdu narration script sized to the chosen duration (approximately
  13–15 Urdu words per 5 seconds — e.g., ~13–15 words for 5s, ~26–30 for 10s,
  ~39–45 for 15s), and exactly one scene description per 5 seconds of the chosen
  duration (1, 2, or 3 scenes).
- **FR-008**: System MUST screen every idea for unsafe or inappropriate content
  (violence, adult, hate, self-harm) and reject matches with a polite, friendly
  message instead of producing a script.
- **FR-009**: System MUST present the corrected idea, the Urdu script (rendered
  right-to-left) with a live word counter against the target for the chosen
  duration, and the scenes, all editable by the Student.
- **FR-010**: System MUST disable the "Approve & Create Video" action whenever
  the live word counter shows the script exceeds the target for the chosen
  duration, re-enabling it once the script is shortened (by edit or regeneration)
  to fit.
- **FR-011**: System MUST let the Student regenerate the script/scenes after
  edits, preserving the scene count required by the chosen duration, and MUST NOT
  start any GPU-based generation (clips or voice) until the Student explicitly
  approves.
- **FR-012**: System MUST start video generation only after the Student clicks an
  explicit approval action ("Approve & Create Video").

**Video Job Processing & Status**

- **FR-013**: System MUST show the Student a progress view with distinguishable
  steps: Preparing, Generating scenes (with a 1/N, 2/N, …, N/N counter where N
  matches the chosen duration's scene count), Adding voice, Finalizing, Ready —
  reflecting the job's actual current step.
- **FR-014**: System MUST persist job progress server-side so a Student who
  navigates away and returns (even in a new browser session) sees the job's real
  current status.
- **FR-015**: Every video job MUST end in exactly one of two terminal states —
  Ready or Failed with a human-readable reason — and MUST NOT remain in a
  processing state indefinitely.
- **FR-016**: System MUST detect jobs that exceed a maximum allowed processing
  duration and automatically mark them Failed with a timeout reason.
- **FR-017**: System MUST, when the spoken narration runs slightly longer than
  the chosen video duration, attempt to speed up the voice audio by at most 10%
  to fit it; if it still does not fit after that adjustment, the system MUST mark
  the job Failed with the reason "Script is too long for the chosen duration —
  please shorten it," and this failure MUST NOT count toward the daily video
  limit.
- **FR-018**: System MUST produce a final video exactly as long as the Student's
  chosen duration (5, 10, or 15 seconds), composed of that duration's required
  number of sequential 5-second scenes (1, 2, or 3), in the Student's chosen
  aspect ratio (16:9 or 9:16); the final video MUST NEVER exceed 15 seconds under
  any circumstance.

**My Videos**

- **FR-019**: System MUST let a Student view only their own videos in a grid
  showing thumbnail, title (derived from their idea), creation date, duration,
  aspect ratio, and status badge (Processing / Ready / Failed).
- **FR-020**: System MUST let a Student play and download (MP4) any of their own
  Ready videos.
- **FR-021**: System MUST let a Student delete any of their own videos that are
  in a terminal state (Ready or Failed); deletion MUST NOT be available while a
  video is Processing.
- **FR-022**: System MUST let a Student retry a Failed video via a "Try again"
  action that creates a new video job from the same approved
  idea/script/duration/aspect ratio/voice.

**Daily Limits**

- **FR-023**: System MUST enforce a daily video-generation limit per Student,
  sourced from server configuration (`DAILY_VIDEO_LIMIT`) and applied equally to
  every Student; there is no per-student override in this version.
- **FR-024**: System MUST show the Student, on the Create page, how many video
  generations they have left for the current day against the configured limit.
- **FR-025**: System MUST block new video generation once a Student's daily video
  limit is reached, with a friendly message stating the limit resets at midnight
  Asia/Karachi time.
- **FR-026**: System MUST NOT count Failed video jobs toward a Student's daily
  video limit.
- **FR-027**: System MUST enforce a separate daily limit on script generations
  (including regenerations) per Student, sourced from server configuration
  (`DAILY_SCRIPT_LIMIT`) and applied equally to every Student, independent of the
  video limit, to prevent abuse of the LLM step.
- **FR-028**: System MUST enforce both daily limits server-side such that no
  client-side manipulation can bypass them.

**Public Pages & UI**

- **FR-029**: System MUST provide a public landing page with: a hero section
  featuring an autoplaying sample video, headline, and "Start Creating" call to
  action; a 3-step "how it works" explanation; a showcase grid of sample videos;
  an FAQ section; and a footer.
- **FR-030**: System MUST provide a light/dark mode toggle available on every
  page, remembering the user's choice across visits and defaulting to the
  system's theme preference when no choice has been made.
- **FR-031**: System MUST render all screens responsively, usable on mobile-width
  viewports first and scaling up to desktop.
- **FR-032**: System MUST display all interface chrome and copy in English, while
  rendering the generated Urdu script and narration text right-to-left.

**Error Handling**

- **FR-033**: System MUST show Students only friendly, non-technical English
  error messages; it MUST NOT expose raw stack traces or internal error details in
  the UI.
- **FR-034**: System MUST log full technical error details server-side, tagged
  with a request or job identifier, for every failure shown to a user.

### Key Entities

- **Student**: A self-registered user with email, hashed password, and a running
  count of videos/scripts generated today and in total. Owns zero or more Video
  Jobs and zero or more Password Reset Tokens.
- **Video Job**: One request to turn an idea into a video. Holds the student's raw
  idea, the LLM-corrected idea, the Urdu narration script, the scene descriptions
  (1, 2, or 3, matching the chosen duration), chosen duration (5/10/15s), chosen
  aspect ratio, chosen voice, current status, failure reason (if any), progress
  step, creation and completion timestamps, and the resulting video/thumbnail
  once Ready. The "Draft/Review" phase (idea entry, script generation/editing)
  happens entirely client-side, before any Video Job row exists — it is never a
  persisted status. Once the Student approves, a Video Job is created and
  progresses through the sequential statuses described in FR-013 (Preparing →
  Generating scenes → Adding voice → Finalizing) to one of the two terminal
  states, Ready or Failed.
- **Scene**: One of the 1–3 ordered 5-second segments belonging to a Video Job
  (count matches the job's chosen duration), with its own scene description text.
- **Password Reset Token**: A time-limited, single-use token tied to one Student,
  with an expiry timestamp and a used/invalidated flag; a new token invalidates
  any previously outstanding token for the same Student.
- **Usage Counter**: Per-student, per-day count of video generations and script
  generations, used to enforce the two server-configured daily limits
  (`DAILY_VIDEO_LIMIT`, `DAILY_SCRIPT_LIMIT`) and reset at midnight Asia/Karachi
  time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new student can sign up and successfully obtain their first Ready
  video without external help or support contact.
- **SC-002**: At least 95% of approved video jobs finish in the Ready state; every
  job (100%) ends in either Ready or Failed — none remain stuck in a processing
  state.
- **SC-003**: The Review screen's live word counter always reflects whether the
  script fits the chosen duration, and approval is only possible when it does
  (no post-approval failures caused by narration length alone, except the rare
  10%-speedup-still-too-long case).
- **SC-004**: A student's daily video-generation limit (from server
  configuration) can never be exceeded, regardless of how generation is
  triggered (0 confirmed bypasses).
- **SC-005**: A student can go from submitting an idea to seeing the Review
  screen in under 30 seconds under normal conditions.
- **SC-006**: All primary screens (Create, Review, Progress, My Videos, password
  reset, landing page) remain fully usable on a mobile-width viewport with no
  horizontal scrolling or obscured controls.
- **SC-007**: A student who forgets their password can regain account access via
  an emailed reset link within a few minutes, without contacting support.

## Assumptions

- No email verification step is required at signup for this version; email +
  password is sufficient to create a Student account. (Explicitly out of scope
  per the feature brief.)
- A video's title is derived automatically from the corrected idea text (e.g., a
  truncated form of it); no separate title field is collected from the student.
- Videos remain available in "My Videos" until the student explicitly deletes
  them; there is no automatic expiry in this version.
- Deleting a video removes it from the student's "My Videos" view and from
  storage; it is not recoverable afterward.
- Rejected (unsafe-content) attempts and failed script-generation calls still
  consume one unit of the daily script-generation limit, since they still invoke
  the LLM.
- `DAILY_VIDEO_LIMIT` and `DAILY_SCRIPT_LIMIT` are global server configuration
  values applied identically to every student; there is no role or UI capable of
  overriding them per student in this version.
- Password-reset emails are delivered via the transactional email service defined
  in the project constitution; no other use of outbound email (e.g., signup
  confirmation, marketing) is in scope here.

## Out of Scope

- Payments or any paid tiers.
- Public sharing or a social/community feed of videos.
- Video timeline editing (trimming, reordering, adding extra clips beyond the
  scene count matching the chosen duration).
- Custom voice cloning; only the two preset voices (Male, Female) are available.
- Narration in any language other than Urdu.
- Videos longer than 15 seconds, or scene counts other than the 1/2/3 implied by
  the chosen 5/10/15-second duration.
- Email verification at signup.
- Any admin role, admin panel, or per-student daily-limit overrides.
