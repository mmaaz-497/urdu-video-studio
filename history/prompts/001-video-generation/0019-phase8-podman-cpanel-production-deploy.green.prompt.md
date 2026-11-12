---
id: 0019
title: Phase 8 podman cPanel production deploy
stage: green
date: 2026-11-12
surface: agent
model: claude-opus-5-5
feature: 001-video-generation
branch: main
user: Maaz
command: (free-form) Phase 8 — production deployment (T091–T095)
labels: ["deployment","podman","cpanel","apache","docker-compose","phase-8"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/plan.md
 - specs/001-video-generation/tasks.md
 - specs/001-video-generation/research.md
 - backend/Dockerfile
 - backend/.dockerignore
 - backend/app/core/config.py
 - backend/app/core/sessions.py
 - backend/app/core/csrf.py
 - backend/app/main.py
 - backend/app/services/ffmpeg_service.py
 - backend/app/services/storage_local.py
 - backend/tests/test_pipeline_hardening.py
 - backend/.env.example
 - frontend/Dockerfile
 - frontend/.dockerignore
 - frontend/next.config.ts
 - frontend/.env.example
 - infra/docker-compose.prod.yml
 - infra/uvs.sh
 - infra/release.sh
 - infra/deploy.sh
 - infra/deploy.env.example
 - infra/.env.production.example
 - infra/apache/ssl/urdu-video-studio.conf
 - infra/apache/std/urdu-video-studio.conf
 - infra/backup/uvs-backup.sh
 - .gitignore
 - README.md
tests:
 - backend pytest full suite (49 passed)
 - tests/test_pipeline_hardening.py::test_ffmpeg_never_inherits_terminal_stdin (extended with thread-cap asserts)
 - local docker run of prod compose: e2e mock jobs through 127.0.0.1:3100, memory caps under load, unordered-start convergence
 - AlmaLinux 8.10 + podman 4.9.4 test VM: podman-compose 1.0.6 vs docker-compose v5.7.1 over podman.socket
 - fake VPS (AlmaLinux 8.10 + podman 4.9.4 + sshd): deploy.sh first deploy, update deploy (re-tag skip), rollback, backup + retention, uvs down -v guard, SSH tunnel login
---

## Prompt

Phase 8 — production deployment (T091–T095). The target server is NOT a clean VPS, so adapt the plan. Update plan.md and tasks.md first (Caddy is dropped).

Verified server facts:
* AlmaLinux 8.10 x86_64, cPanel/WHM 138 with 12 live cPanel accounts. Apache (EA4 httpd) owns ports 80/443 and must stay untouched for those sites.
* 2 vCPU, 3.8 GB RAM (about 2.2 GB available; 1.3 GB of the 4 GB swap already in use), 86 GB disk free.
* No Docker: `docker` is the podman-docker shim. Podman 4.9.4 is installed and already runs another project's Postgres container on 127.0.0.1:5432. Do NOT install docker-ce — on EL8 it would remove podman and break that container.
* Already taken on 127.0.0.1: 3000 (PM2 app), 8000 (python app), 5432 (podman Postgres). Don't touch them.
* No host firewall is active (firewalld inactive, no CSF), so every published port must bind to 127.0.0.1 only.
* SSL will come from cPanel AutoSSL. The domain will be its own cPanel account.

Build:
1. Production images: backend (FastAPI + RQ worker, with ffmpeg) and frontend (Next.js output: "standalone"). Multi-stage, small, non-root.
2. infra/docker-compose.prod.yml that runs under rootful podman 4.9. Choose between podman-compose (EPEL) and the docker-compose v2 binary over podman.socket: verify which one handles our healthchecks and depends_on correctly on podman 4.9, and justify the choice.
   - Services: frontend (127.0.0.1:3100), backend API (127.0.0.1:8100), worker, postgres:16, redis:7.
   - Postgres and Redis publish NO ports.
   - Named volume for the Postgres data.
   - restart: always, and the README must enable podman-restart.service so everything comes back after a reboot.
3. Protect the 12 live sites:
   - memory limits per service, totalling at most ~1.2 GB
   - Redis maxmemory
   - ffmpeg limited to 2 threads and run at low priority (nice)
   - container log rotation
4. Apache reverse proxy include for cPanel EA4, as a template for /etc/apache2/conf.d/userdata/{std,ssl}/2_4/<cpuser>/<domain>/urdu-video-studio.conf:
   - Route /api to 127.0.0.1:8100 and everything else to 127.0.0.1:3100, on the same origin.
   - EXCLUDE /.well-known/ from proxying, so AutoSSL validation keeps working.
   - ProxyPreserveHost, X-Forwarded-Proto https, and sensible proxy timeouts.
   - Make uvicorn trust the proxy headers, so Secure cookies and CSRF work behind Apache.
   - Give the exact commands: the httpd -M check, /scripts/rebuildhttpdconf, /scripts/restartsrv_httpd.
5. No image builds on the VPS (a Next.js build would starve the live sites of RAM). Write infra/deploy.sh, which runs on my WSL machine:
   - Refuse to deploy with uncommitted changes.
   - Build both images with docker and tag them with the git short SHA.
   - Stream them to the VPS: `docker save | gzip | ssh root@$VPS_HOST "gunzip | podman load"`.
   - Upload the compose file, run `alembic upgrade head`, restart the stack, and print a health check.
   - Fail loudly on any error.
6. infra/.env.production.example, documenting every required variable (VIDEO_PROVIDER=runpod, STORAGE_PROVIDER=r2, COOKIE_SECURE=true, APP_BASE_URL, TZ=Asia/Karachi, the DAILY_* limits, MAX_PROCESSING_SECONDS=900, and the rest). The real .env lives only on the VPS, with chmod 600.
7. A daily pg_dump backup via cron on the VPS, keeping 7 days.
8. A README "Deploy" section for a beginner, one command per step: from SSH key setup to the first login on the live domain, plus how to deploy updates and how to roll back to the previous image tag.

Don't run anything against the VPS yourself. Change the app code only where production needs it (proxy headers, standalone output). Report what you built and give me the steps one at a time.
More verified VPS facts for Phase 8:
* Apache already has proxy_module, proxy_http_module, proxy_wstunnel_module and proxy_fcgi_module loaded. No EA4 module installs are needed.
* SELinux is Disabled, so no :Z volume labels are needed.
* Existing podman containers: "tokoshopee-postgres" (127.0.0.1:5432) and "fiv-cobalt" (127.0.0.1:4201). Port 4201 is also taken. Prefix all our container, volume and network names with "uvs-" so nothing collides, and make sure no compose command can ever touch containers outside our project.
* podman-restart.service is enabled. podman.socket is disabled (enable it only if you choose docker-compose v2 over the socket).
* Neither podman-compose nor docker-compose is installed. Give me the exact install command for the tool you choose.
Two more Phase 8 notes:
* The domain is not final yet. Make the deployed stack fully testable before DNS exists, through an SSH tunnel (ssh -L 3100:127.0.0.1:3100 root@VPS, then http://localhost:3100 in the browser). /api must also work through that tunnel, so keep a Next.js rewrite from /api to the backend on the internal network as a fallback. Secure cookies work on http://localhost in Chrome, so COOKIE_SECURE=true can stay. Put the Apache/AutoSSL/DNS steps in a separate "When the domain is ready" README section.
* SSH is on port 22 with root login. deploy.sh should take VPS_HOST and an optional VPS_PORT (default 22) from env or infra/deploy.env (gitignored).

## Response snapshot

Updated plan.md (Design Revision 2026-11-12, Caddy dropped, new Known Risks) and tasks.md (Phase 8 rewritten: T091–T095c). Built backend/frontend production Dockerfiles; prod compose under rootful podman with uvs-* names, 127.0.0.1-only ports, measured memory caps (1232 MB total), Redis maxmemory 32mb noeviction, worker under nice 10 + FFMPEG_THREADS=2, 10 MB log caps, CMD-SHELL healthchecks; /opt/uvs/uvs wrapper; release.sh; deploy.sh (git-archive build, SHA tags, re-tag skip, migrate, health check, rollback); Apache ssl/std includes; .env.production.example; pg_dump backup; README Deploy + "When the domain is ready". Chose Docker Compose v5.7.1 over podman.socket after testing on AlmaLinux 8.10 + podman 4.9.4: EPEL podman-compose 1.0.6 ignores service_healthy, breaks exec-form healthchecks and ignores memswap_limit; also found podman's compat API re-splits exec-form healthcheck args, hence CMD-SHELL. App code changes: COOKIE_SECURE setting, FFMPEG_THREADS cap, next.config output standalone. No commands run against the real VPS.

## Outcome

- ✅ Impact: stack deployable to the shared cPanel VPS without touching Apache's other vhosts or other podman projects; verified end-to-end on a fake AlmaLinux 8.10/podman 4.9.4 VPS via ssh.
- 🧪 Tests: 49 backend tests pass; e2e mock jobs pass locally and on podman; deploy/update/rollback/backup exercised against fake VPS.
- 📁 Files: 2 Dockerfiles + dockerignores, compose, 4 VPS/WSL scripts, 2 Apache includes, env examples, README, spec updates, 6 small backend/frontend edits.
- 🔁 Next prompts: run README Deploy steps 1–7 on the real VPS; later "When the domain is ready"; optionally lazy-import llm_service in video_job_service to shrink scheduler memory.
- 🧠 Reflection: measuring beat estimating — the first memory guesses OOM-killed the scheduler and worker; and the healthcheck re-splitting bug only appeared on real podman.

## Evaluation notes (flywheel)

- Failure modes observed: initial memory caps too low (scheduler 112m, worker 384m OOM); exec-form healthchecks broken on podman compat API; nested-podman reboot test blocked by Docker-in-WSL CNI/iptables quirk (podman-restart at real boot not verified).
- Graders run and results (PASS/FAIL): pytest PASS; shellcheck -S warning PASS (after SC2155 fix); ruff PASS for changed files (pre-existing E501 in runpod_provider.py untouched).
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): lazy import of llm_service in video_job_service, then lower scheduler cap to ~64m.
