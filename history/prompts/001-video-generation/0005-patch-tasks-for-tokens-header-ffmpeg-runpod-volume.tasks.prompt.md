---
id: 0005
title: Patch tasks for tokens, header, ffmpeg, RunPod volume
stage: tasks
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: general (manual tasks.md revision, no slash command)
labels: ["tasks", "design-tokens", "csrf", "same-origin", "runpod-volume", "ffmpeg"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-video-generation/tasks.md
 - specs/001-video-generation/quickstart.md
tests:
 - none (task list only; no code written)
---

## Prompt

Update specs/001-video-generation/tasks.md with these fixes (keep IDs stable by inserting new tasks with suffixes like T034a, and update dependencies):

1. Add a Foundational frontend task: frontend/app/globals.css + tailwind.config.ts — implement ALL design-system.md tokens (light + dark CSS variables mapped to shadcn tokens, radius, shadows, Inter + Noto Nastaliq Urdu font variables, an `.urdu` utility class with dir/line-height rules). Every UI task must use these tokens, no hard-coded colors.
2. Move the shared app header (logo, Create, My Videos, theme toggle, Logout) into Foundational so US1 has navigation and logout from day one; the landing page header in US4 can reuse it.
3. T091 backend/Dockerfile must install ffmpeg (worker and scheduler use the same image). Also list ffmpeg (`sudo apt install ffmpeg`) in quickstart.md prerequisites.
4. Phase 7: add gpu-worker/comfyui/extra_model_paths.yaml pointing ComfyUI at the network volume, and make T083 download these exact files: Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors, Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors, Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan2.2_vae.safetensors, plus mlwithabdullah/omnivoice-urdu-6000.
5. Same-origin API: add a Foundational task for Next.js rewrites so the browser calls /api/* on the frontend origin and it is proxied to the backend in development (in production Caddy routes /api to the backend). Remove the need for CORS-with-credentials; set NEXT_PUBLIC_API_BASE_URL default to /api.

## Response snapshot

Patched `specs/001-video-generation/tasks.md` in place via targeted edits, keeping all 95 original task IDs (T001–T095) stable and inserting 8 new suffixed tasks:

1. **T033a** `frontend/app/globals.css` + `frontend/tailwind.config.ts` (Foundational) — every design-system.md token (light/dark CSS vars, radius, shadows, type scale, Inter + Noto Nastaliq Urdu font vars, `.urdu` utility class). Added a blanket rule (frontend-section note in Phase 3, plus a new Notes-section bullet) that every UI task from Phase 2 onward must style exclusively via these tokens — no hard-coded colors.
2. **T033b** (theme-toggle.tsx), **T033c** (site-header.tsx — logo, Create/My Videos/Logout when authenticated or Login/Start-Creating when anonymous, both states include the theme toggle), **T033d** (`(app)/layout.tsx` mounting T033c) — all moved into Foundational, immediately after T033. Updated T034 (root layout) and T056 (Create page) dependency lines accordingly. In Phase 6 (US4), repurposed T073 into a verification-only task and T074 into `(public)/layout.tsx` that reuses T033c as-is, updating T080's dependency list.
3. Rewrote **T091** to call out the `apt-get install -y ffmpeg` step explicitly and note that `worker`/`scheduler` (T093) share the same backend image; updated T093's description to spell out that those two services just run a different `command:` against T091's image. Added `ffmpeg` (`sudo apt install ffmpeg`) to `quickstart.md`'s Prerequisites list.
4. Rewrote **T083** to enumerate the exact four downloads (three `Comfy-Org` safetensors files by repo+path, plus the full `mlwithabdullah/omnivoice-urdu-6000` repo) and inserted **T083a** (`gpu-worker/comfyui/extra_model_paths.yaml`) between T083 and T084, pointing ComfyUI's model-loader search paths at the network volume; updated T084's dependency from T082 to T083a and reworded it to reference models by name rather than baked-in absolute paths.
5. Inserted **T031a** (`frontend/next.config.ts` + `.env.example` update) right after T031 in Foundational: adds `rewrites()` for same-origin `/api/*` in dev, sets `NEXT_PUBLIC_API_BASE_URL` default to `/api`. Updated T032 (api-client.ts) to depend on T031a and use the relative base. Simplified T026's CORS description (no cross-origin credentialed CORS needed) and T094's Caddyfile description to spell out the `/api/*` → backend / everything-else → frontend production routing split that mirrors T031a's dev-only rewrite.

Also updated: Phase 2's Purpose line, the Foundational Checkpoint text, the Dependencies & Execution Order section (US4 bullet now describes reuse rather than creation), the Parallel Opportunities list (T031a/T033a parallelizable with backend work; T033b→c→d sequential; T073/T074 now "lightweight reuse," not build work; T082/T083 parallel, T083a needs both), and the Notes section (4 new bullets: tokens-only rule, nav/logout-from-Phase-2, same-origin API rationale, ffmpeg-shared-image rationale).

## Outcome

- ✅ Impact: `tasks.md` now captures all 5 requested corrections without renumbering any existing task, preserving every prior cross-reference that didn't need to change.
- 🧪 Tests: none (task-list document; no code written)
- 📁 Files: `specs/001-video-generation/tasks.md` (edited in place, +8 suffixed tasks, now 103 total task lines), `specs/001-video-generation/quickstart.md` (ffmpeg prerequisite added)
- 🔁 Next prompts: Begin implementation at Phase 1, or run `/sp.analyze` for a final cross-artifact consistency pass before writing code.
- 🧠 Reflection: The header move (fix #2) was the trickiest edit — rather than leaving dangling, purposeless task IDs in Phase 6 after moving their content to Foundational, repurposed T073/T074 into legitimate small "reuse/verify" and "mount a public layout" tasks, which keeps the ID-stability constraint satisfied without leaving dead weight in the document.

## Evaluation notes (flywheel)

- Failure modes observed: none — all edits applied as targeted string replacements against the exact existing text, no manual renumbering errors.
- Graders run and results (PASS/FAIL): re-read of the full patched file — PASS (checklist format intact on every line incl. new suffixed IDs; no orphaned dependency references to tasks that no longer do what they're cited for); fix-by-fix checklist against the user's 5 numbered items — PASS (5/5 present and cross-referenced from Notes/Dependencies sections).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
