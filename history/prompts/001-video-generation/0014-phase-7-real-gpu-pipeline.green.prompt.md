---
id: 0014
title: Phase 7 real GPU pipeline
stage: green
date: 2026-11-05
surface: agent
model: claude-sonnet-5-5
feature: 001-video-generation
branch: 001-video-generation
user: Maaz
command: /sp.implement
labels: ["runpod","comfyui","wan2.2","omnivoice","gpu-worker"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - gpu-worker/{volume/LAYOUT.md,scripts/download_weights.sh,scripts/calibrate_words.py,comfyui/extra_model_paths.yaml,workflows/wan22_ti2v5b.json,omnivoice/infer.py,handler.py,Dockerfile,requirements.txt}
 - backend/app/services/{runpod_provider.py,video_pipeline.py,ffmpeg_service.py}
 - backend/tests/test_runpod_pipeline.py
 - backend/pyproject.toml
 - specs/001-video-generation/tasks.md
tests:
 - backend/tests/test_runpod_pipeline.py (6 new); full suite 40 passed; ruff clean on changed files
---

## Prompt

/sp.implement Implement Phase 7 (Real GPU Pipeline, T082–T090) from specs/001-video-generation/tasks.md. Write code only — do not run anything on RunPod. Deliverables: volume LAYOUT.md, download_weights.sh, extra_model_paths.yaml, wan22_ti2v5b.json workflow, omnivoice/infer.py, handler.py (R2 presigned PUT, 30s timeout, 2 retries, progress_update, return narration duration), Dockerfile (no weights), runpod_provider.py (30s timeout, 3 retries, RUNPOD_UNAVAILABLE), video_pipeline.py branch on VIDEO_PROVIDER sharing the FFmpeg finalize, plus scripts/calibrate_words.py. Keep mock working; run pytest and ruff; add runpod-branch test with mocked provider; mark tasks [X]; report files, tests, RunPod next steps. (Full original text abridged here to the deliverable list.)

## Response snapshot

Implemented all T082–T090 + calibrate_words.py. Mock path refactored to share `_finalize`. Untested against real RunPod/ComfyUI/OmniVoice.

## Outcome

- ✅ Impact: VIDEO_PROVIDER=runpod path implemented behind mocks; mock unchanged.
- 🧪 Tests: 40 passed.
- 🔁 Next prompts: deploy on RunPod, calibrate words, Phase 8.
- 🧠 Reflection: workflow JSON and SDK progress parsing are unverified until a real run.
