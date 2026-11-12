---
id: 0016
title: Subtle 3D design pass for all pages
stage: green
date: 2026-11-11
surface: agent
model: claude-fable-5-2
feature: 001-video-generation
branch: main
user: Maaz
command: direct request
labels: ["frontend","design-system","3d","elevation","tailwind"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - frontend/app/globals.css, frontend/tailwind.config.ts
 - frontend/components/ui/{tilt,button,card,input,textarea}.tsx
 - frontend/components/marketing/{hero,how-it-works,showcase-grid,faq-accordion,reveal,site-footer}.tsx
 - frontend/components/layout/site-header.tsx
 - frontend/components/studio/{option-card,video-card,progress-stepper,usage-badge}.tsx
 - frontend/app/(auth)/layout.tsx and the login, register, forgot-password, reset-password pages
 - frontend/app/(app)/{create,review,videos}/page.tsx, frontend/app/(app)/videos/[id]/progress/page.tsx
 - specs/001-video-generation/design-system.md
tests:
 - npx tsc --noEmit (pass); npm run lint (pass); npm run build (pass)
 - Playwright screenshots of all 10 routes, dark and light, 1440px and 390px, API mocked: no page errors, no horizontal overflow
 - e2e/download.spec.ts not run (needs E2E_* credentials)
---

## Prompt

Hi, analyze this project and give all its UI pages, from the Homepage onward, a subtle 3D design style to create a more premium, modern, and visually appealing look.

## Response snapshot

Planned and implemented a CSS-only depth pass with no new dependencies. Added per-theme depth tokens (three elevation levels, lit top edge, recessed well, CTA glow) and `surface-3d` / `lift` / `tilt` utilities; a mouse-only `Tilt` component; a `gradient` button variant replacing the repeated gradient class string; recessed inputs; and applied the levels across the landing page (tilted hero video, floating narration chip, lifting step cards, tilting showcase cards, raised FAQ panel), the four auth pages (rise-in cards, second background glow) and the studio pages (option cards, video cards, stepper, scene cards, player frame). Layout, copy, colours and behaviour are unchanged; tilt and lift are disabled under reduced motion.

## Outcome

- ✅ Impact: All 10 routes share a consistent three-level depth system in both themes.
- 🧪 Tests: Type-check, lint and production build pass; screenshots of every route reviewed in both themes.
- 📁 Files: 27 frontend files changed, 1 added (tilt.tsx), design-system.md updated.
- 🔁 Next prompts: Run e2e/download.spec.ts with credentials; decide whether to fix the clipped Urdu title input on /review (pre-existing).
- 🧠 Reflection: Running `next build` while the user's `next dev` was using the same `.next` folder corrupted the dev server's cache; verification should use a separate copy from the start.

## Evaluation notes (flywheel)

- Failure modes observed: Prettier run on unformatted files added unrelated diff noise (removed via three-way merge); build clashed with running dev server.
- Graders run and results (PASS/FAIL): tsc PASS, eslint PASS, next build PASS, visual review PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Measure whether the hero resting tilt should be reduced from 6° to 4°.
