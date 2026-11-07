---
id: 0015
title: Per-scene narration and attachment download
stage: green
date: 2026-11-07
surface: agent
model: claude-sonnet-5-5
feature: 001-video-generation
branch: main
user: Maaz
command: direct request
labels: ["narration-sync","per-scene","download","presigned-url","playwright"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/{spec,plan,tasks,data-model}.md, contracts/openapi.yaml
 - backend/app/services/{llm_service,ffmpeg_service,video_pipeline,runpod_provider,video_job_service,storage_*}.py
 - backend/app/api/{scripts,videos}.py, backend/app/schemas/{scripts,videos}.py
 - gpu-worker/handler.py, frontend review page, download-button.tsx, e2e/download.spec.ts
tests:
 - backend pytest (49 passed, isolated test DB); Playwright download check on R2 and local storage
---

## Prompt

Two fixes: (1) narration not synced to visuals -> per-scene {visual_prompt, narration_ur} through LLM, review UI, GPU worker and FFmpeg assembly (spec first); (2) Download button expands the video instead of downloading -> confirm cause, add owner-only presigned attachment endpoint (R2 + local), verify with Playwright. Keep tests minimal; verify with one mock run and one real OpenAI call; say if a worker rebuild is needed. (Full text in the session transcript.)

## Response

Specs updated first. Download root cause confirmed in Chromium against real R2: cross-origin `<a download>` ignored, tab navigated to the raw MP4. Implemented per-scene pipeline + `GET /videos/{id}/download`. Verified: real OpenAI call, mock run (speech restarts at 5.0 s / 10.0 s), Playwright download on R2 and local. Worker image rebuild required.
