# Quickstart: Local Development (Ubuntu / WSL)

This walks through running the full student video flow locally, for free,
using `VIDEO_PROVIDER=mock` — no GPU, no RunPod account, no real OpenAI/email
spend required to see the end-to-end flow (a real `OPENAI_API_KEY` is still
needed for the script-generation step, since there's no "mock LLM").

## Prerequisites

- Ubuntu 22.04+ inside WSL2 (or native Ubuntu/Linux).
- Docker + Docker Compose plugin.
- Node.js 20+ and `npm`.
- Python 3.12 + `pip` (or `poetry`/`uv`, per `backend/` setup).
- `ffmpeg` on your PATH — `sudo apt install ffmpeg` (used by the backend/worker for clip normalization, voice-speed correction, and thumbnail generation, even in `VIDEO_PROVIDER=mock`).
- An OpenAI API key (for the LLM correction/script step — not mockable).

## 1. Clone and configure environment

```bash
git clone <repo-url> urdu-video-studio && cd urdu-video-studio
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env` and set at minimum:

```dotenv
# Core
DATABASE_URL=postgresql+psycopg://urdu_video:urdu_video@localhost:5432/urdu_video_studio
REDIS_URL=redis://localhost:6379/0

# Video pipeline
VIDEO_PROVIDER=mock          # "mock" = free, no GPU. "runpod" = real generation.

# LLM
OPENAI_API_KEY=sk-...        # required even in mock mode
OPENAI_MODEL=gpt-4o-mini      # or your current small/cheap model of choice

# Daily limits (server configuration — see constitution v2.0.0)
DAILY_VIDEO_LIMIT=5
DAILY_SCRIPT_LIMIT=20

# Password reset email (Resend — see research.md A2)
RESEND_API_KEY=re_...
EMAIL_FROM="Urdu Video Studio <noreply@yourdomain.test>"

# Storage (Cloudflare R2 — S3-compatible)
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=urdu-video-studio-dev

# Session
SESSION_COOKIE_SECRET=<openssl rand -hex 32>
SESSION_TTL_SECONDS=1209600  # 14 days

# Only needed if VIDEO_PROVIDER=runpod
RUNPOD_API_KEY=
RUNPOD_ENDPOINT_ID=
```

> Even in `mock` mode, R2 credentials are required because the mock pipeline
> still uploads the bundled sample assets through the same FFmpeg → R2 upload
> code path as production (see research.md A8) — this is what keeps dev/prod
> parity real. Use a free Cloudflare R2 bucket for local development.

## 2. Start Postgres + Redis

```bash
docker compose -f infra/docker-compose.dev.yml up -d
```

This starts **only** Postgres and Redis in containers — frontend and backend
run natively for hot reload, per the constitution's local-dev policy.

## 3. Backend: migrate and run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal, start the RQ worker (processes video jobs):

```bash
cd backend && source .venv/bin/activate
python -m app.worker
```

In a third terminal, start the stale-job sweeper:

```bash
cd backend && source .venv/bin/activate
python -m app.scheduler
```

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

## 5. Walk the flow

1. Sign up with any email/password at `/register`.
2. Go to `/create`, type an idea (10–500 chars, Roman Urdu or Urdu), pick a
   duration (5/10/15s), aspect ratio, and voice.
3. Click "Generate Script" — this is a **real** OpenAI call (uses your
   `OPENAI_API_KEY`); everything after this step is mocked.
4. On the Review screen, confirm the word counter is under the target, then
   "Approve & Create Video."
5. Watch the progress view move through Preparing → Generating scenes (1/N…
   N/N) → Adding voice → Finalizing → Ready — using bundled sample clips/voice
   instead of RunPod, in a few seconds.
6. Open "My Videos," play/download the Ready video.
7. Try "Forgot password" from the login screen — with `RESEND_API_KEY` set,
   check the inbox of the email you registered with (or Resend's dashboard
   logs in sandbox mode) for the reset link.

## 6. Running the critical-path tests

```bash
cd backend && source .venv/bin/activate
pytest tests/test_auth.py tests/test_video_job_state_machine.py tests/test_llm_output_parsing.py
```

Per Constitution Principle VII, these three files are the only required
automated tests for this feature — no broader suite is expected.

## 7. Manual performance & responsiveness spot-check

These budgets are verified manually for v1 (no automated load test or
responsive-layout test is in scope per Constitution Principle VII):

- Time step 3 above (idea submit → Review screen render) — confirm it's
  comfortably under 30 seconds (SC-005) on a normal connection.
- With your browser's device toolbar set to a 375px-wide viewport, click
  through Create → Review → Progress → My Videos → Forgot password → Reset
  password and the public landing page. Confirm every screen is usable with
  no horizontal scrolling and no obscured controls (FR-031, SC-006).

## Switching to real GPU generation

Set `VIDEO_PROVIDER=runpod` and provide `RUNPOD_API_KEY` /
`RUNPOD_ENDPOINT_ID` for a deployed `gpu-worker/` RunPod Serverless endpoint.
Everything else (API, DB, FFmpeg assembly, polling UI) is unchanged — the
provider switch is the only thing that changes (constitution's `VIDEO_PROVIDER`
contract).
