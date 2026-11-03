# Phase 0 Research: Student Video Generation

This document resolves every technical decision needed before design (Phase 1),
using the Decision / Rationale / Alternatives Considered format. It covers (A)
backend/pipeline/infrastructure decisions and (B) UI design research into
comparable AI video products, which feeds `design-system.md`.

## A. Backend, Pipeline & Infrastructure Decisions

### A1. Session strategy: server-side Redis session vs. JWT

**Decision**: Opaque, random session ID in an httpOnly, Secure, SameSite=Lax
cookie; session data (`student_id`, `expires_at`) stored in Redis under
`session:<id>`, with a sliding or fixed TTL matching FR-002's "until logout or
session expires."

**Rationale**: Redis is already a mandated part of the fixed stack (for RQ), so
this adds zero new infrastructure. Logout is a single `DEL`. There is no token-
revocation problem to solve (unlike JWT, where invalidating a single compromised
token before its natural expiry requires a denylist — which is itself a server-
side session store, just reinvented). This is the simplest option that satisfies
Principle I.

**Alternatives considered**:
- *Stateless JWT in an httpOnly cookie*: avoids a Redis round-trip per request,
  but immediate logout/revocation requires a denylist (back to server-side
  state), and refresh-token rotation adds meaningful complexity for a feature
  that doesn't need horizontal auth-service scaling. Rejected as unnecessary
  complexity for this project's scale.
- *Starlette's built-in `SessionMiddleware`*: signs the whole session payload
  into the cookie itself (no server lookup), but that payload is visible
  (though signed, not encrypted) to the client and cookies have a ~4KB ceiling;
  using it would mean the convention gets outgrown as soon as session data
  grows. Rejected in favor of the Redis-backed approach, which scales trivially.

### A2. Transactional email provider (for password reset)

**Decision**: **Resend** (resend.com), via its REST API, behind a small
provider-agnostic `EmailSender` protocol/interface in `backend/app/services/email_service.py`.

**Rationale**: Resend's free tier (3,000 emails/month, 100/day at time of
writing) comfortably covers a password-reset-only use case for an educational
project's expected volume. Its API is a single HTTP POST with a simple SDK,
requiring no SMTP connection management. Wrapping it behind a one-method
interface (`send(to, subject, html) -> None`) means swapping providers later
(e.g., if free-tier limits are exceeded) touches one file, not every call site —
satisfying Principle II's "propose before adding, keep it swappable" spirit.

**Alternatives considered**:
- *AWS SES*: cheaper at scale and already AWS-grade reliable, but requires
  domain verification, sandbox-mode removal (a support request with turnaround
  time), and IAM credential setup — meaningfully more operational setup for a
  single-purpose, low-volume email need. Rejected for this project's scale.
- *Postmark*: excellent deliverability reputation for transactional email, but
  its free tier is a time-limited trial rather than an ongoing free allowance.
  Rejected to avoid a future forced migration.
- *SMTP via a generic library (e.g., `smtplib`)* against any provider: provider-
  agnostic in theory, but loses delivery-tracking/webhook features and still
  needs *a* provider's SMTP credentials — no real simplicity win over a REST API
  SDK. Rejected.

### A3. Idempotent job creation + atomic daily-limit enforcement

**Decision**: The client generates a UUID `idempotencyKey` when the student
clicks "Approve & Create Video" and sends it in the request body. The backend,
in a single DB transaction:
1. `SELECT ... FOR UPDATE` the student's `usage_counter` row for today's date
   (row lock — serializes concurrent requests from the same student).
2. Check a unique `(student_id, idempotency_key)` constraint on `video_jobs`:
   if a job with that key already exists, return it as-is (idempotent replay,
   no double-create, no double-increment).
3. Otherwise check `video_jobs_count_today < DAILY_VIDEO_LIMIT`; if exceeded,
   roll back and return the friendly limit-reached error.
4. Otherwise insert the new `VideoJob` row (status `queued`) and increment the
   counter, then commit.
5. Only *after* a successful commit does the backend enqueue the RQ task —
   never inside the transaction — so a crash between commit and enqueue is
   recoverable by the stale-job sweeper (A7), and a rollback never leaves an
   orphaned queue message.

**Rationale**: This is the standard "check-then-act under a row lock" pattern
for preventing both double-submission (FR duplicate-click edge case) and limit
bypass (FR-023/FR-028, SC-004) with one well-understood primitive already
available in Postgres/SQLAlchemy — no new library needed.

**Alternatives considered**:
- *Redis `INCR` with a TTL as the counter*: faster, but moves the source of
  truth for a business rule (daily limits) into a cache that isn't the system
  of record and complicates the "0 confirmed bypasses" guarantee (SC-004) if
  Redis and Postgres ever disagree after a crash. Rejected in favor of Postgres
  as the single source of truth; Redis remains the queue/session store only.
- *Advisory locks / SERIALIZABLE isolation*: achieves the same guarantee but
  with less locality and harder-to-reason-about failure modes than a plain row
  lock on a counter row scoped to `(student_id, date)`. Rejected as unnecessary.

### A4. ComfyUI / Wan 2.2 TI2V-5B invocation from the GPU worker

**Decision**: `gpu-worker/handler.py` is a RunPod Serverless handler that (a)
starts headless ComfyUI in the worker container, (b) loads a pre-authored
API-format workflow JSON template (`workflows/wan22_ti2v5b.json`) using the
official Wan 2.2 TI2V-5B nodes, (c) for each of the 1–3 scenes, substitutes the
scene's English prompt, resolution (16:9 → 1280×704, 9:16 → 704×1280), and
frame count (121 frames @ 24fps ≈ 5s) into the template and submits it to
ComfyUI's `/prompt` API, (d) polls ComfyUI's `/history`/websocket progress for
each scene and calls `runpod.serverless.progress_update()` after each scene
completes so the RQ worker can map "scene i/N done" to the job's progress step.

**Rationale**: This is the standard, documented way to drive ComfyUI
programmatically (export a workflow as API-format JSON once, then parameterize
it per request) and keeps the GPU worker a thin orchestration layer around the
officially-supported workflow rather than a from-scratch inference pipeline.

**Alternatives considered**: Calling the Wan 2.2 model directly via `diffusers`/
raw PyTorch instead of ComfyUI was not considered a real alternative — the
constitution fixes "Wan 2.2 TI2V-5B via ComfyUI" as the stack, so this section
only resolves *how* to drive ComfyUI headlessly, not *whether* to use it.

### A5. OmniVoice Urdu TTS integration

**Decision**: The GPU worker's `omnivoice/` module wraps
`mlwithabdullah/omnivoice-urdu-6000` inference with two fixed reference-voice
audio prompts (male, female) bundled into the worker image. For a job, it
synthesizes the full narration script against the chosen voice's reference
audio in one pass (not per-scene), producing a single narration track that the
backend later aligns against the concatenated clips.

**Rationale**: Synthesizing narration once (not per-scene) avoids audible seams
between scene-boundary voice segments and matches how the backend's FFmpeg step
treats "the voice track" as a single overlay onto the concatenated clips.

**Alternatives considered**: Per-scene narration synthesis (one TTS call per
scene, concatenated) was considered to parallelize scene video-gen and voice-gen,
but rejected — it reintroduces exactly the seam/pacing problem a single-pass
narration avoids, for a marginal latency win on jobs that are already dominated
by clip generation time, not TTS time.

### A6. Narration-to-duration fit: atempo fallback, then fail

**Decision**: After FFmpeg concatenates the normalized clips to the chosen
duration, if the narration track's length exceeds the video's length, FFmpeg's
`atempo` filter speeds the audio up by `min(narration_len / video_len, 1.10)`
(i.e., at most a 10% speedup, per FR-017). If after that the sped-up narration
*still* exceeds the video length, the job is marked `failed` with reason
"Script is too long for the chosen duration — please shorten it," and this does
not increment the daily video-job count (A3's counter is decremented, or more
precisely: the increment in A3 happens on *job creation*, so a later failure
here must trigger a compensating decrement of `video_jobs_count_today` — see
data-model.md's Usage Counter notes).

**Rationale**: `atempo` is FFmpeg's standard pitch-preserving tempo filter and
natively supports the 0.5–2.0 range, so a 1.00–1.10 speedup is a trivial,
well-supported case. This directly implements FR-017 with no new dependency.

**Alternatives considered**: Time-stretching the *video* instead of the audio
(playing clips slightly faster) was rejected — it would violate FR-018's "final
video MUST equal the chosen duration" and visibly distort motion; speeding the
voice slightly is imperceptible up to ~10% and exactly what the spec calls for.

### A7. Stale-job sweeper & job progress model

**Decision**: A lightweight periodic task (RQ's own scheduling via a repeating
job, or a simple `while True: sleep(N); run()` loop in a dedicated `scheduler.py`
process started alongside the worker) scans `video_jobs` for rows in a
non-terminal status whose `created_at` is older than `MAX_PROCESSING_SECONDS`
(env-configurable) and marks them `failed` with reason "This took too long —
please try again," decrementing the daily counter per A3/A6.

**Rationale**: Directly implements Constitution Principle V ("a background
process MUST detect and mark stale/orphaned jobs as failed") and spec FR-015/
FR-016 without introducing a new scheduling library (`rq-scheduler` is an option
but a plain interval loop is simpler and sufficient at this scale — Principle I).

**Alternatives considered**: `rq-scheduler` / `celery beat`-style cron inside
the job queue was considered but rejected as an unneeded dependency for a single
periodic check; a plain loop process is simpler and auditable in under 5 minutes
(Principle I).

### A8. `VIDEO_PROVIDER=mock` implementation

**Decision**: When `VIDEO_PROVIDER=mock`, the RQ worker skips RunPod entirely:
it picks one bundled sample clip set per (aspect ratio × scene count)
combination and a bundled sample voice clip per chosen voice from
`backend/app/services/mock_provider/assets/`, waits a short simulated delay per
step (so the progress view still visibly moves through Preparing → Generating
scenes → Adding voice → Finalizing → Ready), then runs the *same* FFmpeg
assembly code path (A6) against the sample assets. This guarantees dev/prod
parity in the assembly logic — only the clip/voice *source* differs.

**Rationale**: Exercises the full state machine, progress UI, and FFmpeg
pipeline for free, locally, matching the constitution's `VIDEO_PROVIDER` gate
requirement precisely.

**Alternatives considered**: A separate "fake" status-transition code path that
bypasses FFmpeg entirely was rejected — it would let the assembly logic silently
rot un-exercised in local development, undermining the whole point of parity.

### A9. Content moderation & LLM structured output

**Decision**: Before the correction/script-writing agent call, the idea text is
sent to OpenAI's moderation endpoint; a flagged result short-circuits with the
friendly rejection message (FR-008) and still increments the script-generation
counter (per spec Assumptions). The script-writing step uses the OpenAI Agents
SDK with a Pydantic output model (`corrected_idea: str`, `urdu_script: str`,
`scenes: list[str]` with length constrained to the duration's required count,
`title: str`). The backend additionally re-validates scene count and a
word-count ceiling server-side (never trusting the model's self-report); on an
invalid result it retries the generation call exactly once, then surfaces a
friendly "couldn't generate a script, please try again" error.

**Rationale**: Directly implements FR-007/FR-008 and the "validate output...
retry once... friendly error" instruction; Pydantic validation plus a server-
side re-check is the standard structured-output-SDK pattern and needs no new
dependency beyond the already-fixed OpenAI Agents SDK.

**Alternatives considered**: Trusting the SDK's schema validation alone (no
independent server-side recount) was rejected — scene *count* and word *count*
are business rules this spec treats as hard gates (FR-010, FR-017), not just LLM
formatting concerns, so the backend re-checks them independently of whatever the
model claims.

### A10. Polling vs. WebSockets for progress updates

**Decision**: TanStack Query `refetchInterval: 3000` against `GET
/videos/{id}`, per the brief's explicit instruction. No WebSocket/SSE channel.

**Rationale**: At this project's scale (low hundreds of students, jobs that take
minutes not milliseconds to progress), a 3s poll is negligible load and avoids
the connection-lifecycle complexity of WebSockets (reconnect-on-navigate,
server-side pub/sub fan-out) for a UI need that doesn't require sub-second
updates. Matches Principle I.

**Alternatives considered**: Server-Sent Events or WebSockets would reduce
request volume marginally but add meaningful backend complexity (long-lived
connections behind Caddy, reconnect handling across the "leave and come back"
requirement in FR-014) for no user-perceptible benefit at 3s granularity.
Rejected.

## B. UI Design Research (feeds design-system.md)

Researched the public landing pages and, where accessible, generation
workspaces of category-leading AI video tools to extract *patterns*, not assets
— no logos, brand names, or copy are reused anywhere in this project.

- **Runway** (runway.com): hero-first layout, dark-leaning high-contrast
  backgrounds with bright accent CTAs, confident/aspirational short-headline
  copy ("Create anything, anytime"), modular feature cards, clear single-action
  CTA buttons ("Try now").
- **Pika** (pika.art): a lighter, cleaner counterpoint — light background,
  dark text, sans-serif throughout, tool capabilities as a scannable grid of
  cards each with its own preview + CTA, and a "Made with Pika" community
  gallery grid (thumbnail + creator attribution) as social proof.
- **Higgsfield** (higgsfield.ai): strongly dark-mode, modular card-based
  showcase of model/feature combinations with autoplaying video previews
  inside cards, bold/punchy capability-first headlines, consistent "Start
  generating" CTA language.
- **Kling AI / Luma Dream Machine** (via comparison sources, since both gate
  their actual workspace behind login): both expose duration and aspect-ratio
  as explicit, discrete selector options in the generation UI (e.g., 16:9 /
  9:16 / 1:1 cards; duration presets rather than a free-form slider), confirming
  that "visual option cards" for aspect ratio + duration (as this spec already
  requires, FR-006) is the category-standard interaction, not a novel choice.
- **Runway Gen-3 / Hailuo (MiniMax) via Higgsfield**: both treat duration as a
  small set of fixed presets (e.g., Runway Gen-3's 5–10s range in whole-second
  steps; Hailuo's 6–10s or 10–15s), reinforcing that quantized duration choices
  (this spec's 5/10/15s) match how users in this category already expect to
  choose length — not a continuous slider.

**Synthesis / Decision for this project**: Adopt a **dark-first, premium**
visual language (matching the Runway/Higgsfield end of the spectrum, since that
reads as "serious creative tool" rather than "consumer toy") while keeping light
mode equally first-class per the constitution's UI standard — not a dim
afterthought. Concretely: a hero section with an autoplaying muted sample video
as the background/centerpiece (common across every tool researched), a short
punchy headline + single primary CTA, quantized option-cards for duration/
aspect-ratio/voice (not sliders or dropdowns, matching Kling/Luma/Runway/Hailuo
convention), a labeled step-by-step progress indicator (not a bare spinner —
every tool researched shows *what* is happening, not just *that* something is
happening), and a hover-preview grid for both the public showcase and "My
Videos" (matching Pika's gallery and Higgsfield's card pattern). Full tokens and
component mapping are specified in `design-system.md`.

**Alternatives considered**: A light-first, "SaaS dashboard" look (closer to
generic B2B tools) was considered and rejected — none of the researched category
leaders default to that aesthetic, and the constitution explicitly calls for a
"premium, modern" feel, which this category's dark-first convention serves
better while this project still ships an equally polished light mode (per
constitution, not optional).

**Sources consulted**:
- [Runway](https://runway.com/)
- [Pika](https://pika.art)
- [Higgsfield AI](https://higgsfield.ai)
- [Kling Review 2026](https://lumalabs.ai/news/kling-review)
- [Kling vs Pika vs Luma: AI Video Model Comparison 2026](https://melies.co/kling-vs-pika-vs-luma)
- [Runway Gen-3 AI Video Guide and Tutorial](https://blog.segmind.com/runway-gen-3-ai-video-guide-tutorial/)
- [Meet MiniMax H3 on Higgsfield](https://higgsfield.ai/blog/minimax-h3-higgsfield)

## Outstanding NEEDS CLARIFICATION

None. All Technical Context unknowns are resolved above.
