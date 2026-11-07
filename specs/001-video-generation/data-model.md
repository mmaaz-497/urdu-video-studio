# Data Model: Student Video Generation

Derived from `spec.md`'s Key Entities, tightened with concrete types/constraints
for the fixed stack (PostgreSQL via SQLAlchemy 2). Timestamps are UTC; "today"
for daily-limit purposes is computed in the Asia/Karachi calendar day (per
FR-025/FR-027), not UTC midnight.

## Modeling note: no separate "Script Draft" table

The spec's Review screen (edit → regenerate → approve) does not require
persisting in-progress script drafts server-side: each "Generate Script" /
"regenerate" call is a stateless request (idea + duration + aspect ratio + voice
in, corrected idea + script + scenes + title out), held in frontend state until
the student clicks Approve. At that point, the (possibly student-edited)
corrected idea/script/scenes/selections are submitted directly in the
`POST /videos` body, which is also when a `VideoJob` row is first created. This
keeps the data model smaller (Principle I) — nothing is lost, since the spec
never requires resuming an *unapproved* draft across a page reload, only resuming
an *approved, in-progress* job (FR-014).

## Entities

### Student

| Field | Type | Constraints |
|---|---|---|
| `id` | UUID (PK) | default `gen_random_uuid()` |
| `email` | citext / text | UNIQUE, NOT NULL, validated as an email address |
| `password_hash` | text | NOT NULL — argon2 hash, never the plaintext |
| `created_at` | timestamptz | NOT NULL, default now() |
| `last_login_at` | timestamptz | nullable |

Relationships: one Student has many `VideoJob`, many `PasswordResetToken`, many
`UsageCounter` (one per calendar day it has activity).

Validation (app-level, not just DB): email format RFC-5322-reasonable; password
minimum 8 characters at registration/reset (a reasonable default — not specified
by the spec, documented here as an assumption). No role column exists —
constitution v2.0.0 has a single role.

### VideoJob

| Field | Type | Constraints |
|---|---|---|
| `id` | UUID (PK) | default `gen_random_uuid()` |
| `student_id` | UUID (FK → Student) | NOT NULL |
| `idempotency_key` | text | NOT NULL; UNIQUE together with `student_id` |
| `raw_idea` | text | NOT NULL, 10–500 chars (FR-005) |
| `corrected_idea` | text | NOT NULL |
| `title` | text | NOT NULL — derived from `corrected_idea` |
| `urdu_script` | text | NOT NULL — the per-scene narrations joined in order (derived server-side; display/back-compat only) |
| `scenes` | JSONB (array of `{visualPrompt, narrationUr}`) | NOT NULL; length MUST equal `duration_seconds / 5`; each `narrationUr` non-empty and ≤12 words. No migration: the column was already JSONB. Rows created before this change hold plain strings (visual prompt only); they are read as `{visualPrompt: s, narrationUr: ""}` and cannot be retried |
| `duration_seconds` | smallint | NOT NULL; CHECK IN (5, 10, 15) |
| `aspect_ratio` | text | NOT NULL; CHECK IN ('16:9', '9:16') |
| `voice_id` | text | NOT NULL; CHECK IN ('male', 'female') |
| `status` | text | NOT NULL; CHECK IN (see State Transitions); default `'queued'` |
| `progress_current_scene` | smallint | nullable; 0..`progress_total_scenes` |
| `progress_total_scenes` | smallint | NOT NULL; = `duration_seconds / 5` |
| `failure_reason` | text | nullable; set only when `status = 'failed'` |
| `counted_toward_limit` | boolean | NOT NULL default `true` — see Usage Counter notes |
| `video_url` | text | nullable; R2 object key/URL, set when `status = 'ready'` |
| `thumbnail_url` | text | nullable; set when `status = 'ready'` |
| `created_at` | timestamptz | NOT NULL, default now() |
| `updated_at` | timestamptz | NOT NULL, default now(), updated on every status change |
| `completed_at` | timestamptz | nullable; set when reaching `ready` or `failed` |

Indexes: `(student_id, created_at DESC)` for "My Videos"; `(status, created_at)`
for the stale-job sweeper (A7 in research.md).

Relationships: belongs to one `Student`. `scenes` is an embedded JSONB array
(see modeling note above) rather than a child table — scenes have no identity
or lifecycle independent of their job.

#### State Transitions

```text
queued → preparing → generating_scenes → adding_voice → finalizing → ready
   │           │               │               │             │
   └───────────┴───────────────┴───────────────┴─────────────┴──→ failed
```

- `queued`: row created, RQ task not yet picked up (or `VIDEO_PROVIDER=mock`
  substituting bundled assets).
- `preparing`: RQ worker claimed the job, submitting to RunPod (or mock setup).
- `generating_scenes`: GPU worker rendering clips; `progress_current_scene`
  increments 1..N as each scene's `runpod.serverless.progress_update()` lands.
- `adding_voice`: OmniVoice synthesis in progress.
- `finalizing`: backend FFmpeg assembly (normalize/concat/atempo-fit/thumbnail/
  upload) in progress.
- `ready`: terminal success; `video_url`/`thumbnail_url` set.
- `failed`: terminal failure from **any** prior state; `failure_reason` set.
  Reachable via: content/validation error, RunPod error, narration-still-too-
  long-after-10%-speedup (FR-017), timeout (FR-016/stale sweeper).
- Terminal states (`ready`, `failed`) are immutable — "Try again" (FR-022)
  always creates a **new** `VideoJob` row with a new `idempotency_key`, never
  mutates a terminal one.
- Deletion (FR-021) is only permitted from `ready` or `failed`.

### Password Reset Token

| Field | Type | Constraints |
|---|---|---|
| `id` | UUID (PK) | default `gen_random_uuid()` |
| `student_id` | UUID (FK → Student) | NOT NULL |
| `token_hash` | text | NOT NULL, UNIQUE — SHA-256 of the raw token; the raw token is only ever in the emailed URL, never stored |
| `expires_at` | timestamptz | NOT NULL — `created_at` + a short fixed window (e.g., 30 minutes) |
| `used_at` | timestamptz | nullable — set when successfully consumed |
| `invalidated_at` | timestamptz | nullable — set when superseded by a newer token request |
| `created_at` | timestamptz | NOT NULL, default now() |

Validity rule (FR-004, edge cases): a token is usable only if `now() <
expires_at AND used_at IS NULL AND invalidated_at IS NULL`. Issuing a new token
for a student sets `invalidated_at = now()` on any still-outstanding prior token
for that student in the same transaction.

### Usage Counter

| Field | Type | Constraints |
|---|---|---|
| `student_id` | UUID (FK → Student) | part of composite PK |
| `usage_date` | date | part of composite PK — the Asia/Karachi calendar date |
| `video_count` | integer | NOT NULL, default 0 |
| `script_count` | integer | NOT NULL, default 0 |

PK: `(student_id, usage_date)`. This is the row locked with `SELECT ... FOR
UPDATE` during job creation and script generation (research.md A3), making
limit enforcement atomic per student per day. `video_count` is incremented on
`VideoJob` creation and **decremented** (floor 0) if that same job later fails
for a reason excluded from the limit (every failure reason in this spec is
excluded — FR-026) — equivalently, `video_count` can be implemented as "jobs
created today that have not yet failed," reconciled via the `counted_toward_limit`
flag on `VideoJob` at read time for the "X of Y left today" display (FR-024), to
avoid a race between the increment-on-create and decrement-on-fail transactions.
`script_count` increments on every `/scripts` call (including rejected/unsafe
ones, per the spec's Assumptions) and is never decremented.

## Relationships Summary

```text
Student 1──* VideoJob
Student 1──* PasswordResetToken
Student 1──* UsageCounter   (one row per active day)
```

No entity in this feature has a many-to-many relationship; everything hangs off
`Student` by a simple foreign key.
