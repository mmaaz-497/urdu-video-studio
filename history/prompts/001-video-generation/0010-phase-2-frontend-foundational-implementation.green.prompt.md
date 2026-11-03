---
id: 0010
title: Phase 2 frontend foundational implementation
stage: green
date: 2026-11-02
surface: agent
model: claude-sonnet-5
feature: 001-video-generation
branch: 001-video-generation
user: mmaazjatt497@gmail.com
command: /sp.implement
labels: ["frontend", "design-system", "auth", "nextjs", "foundational"]
links:
  spec: specs/001-video-generation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - frontend/next.config.ts
 - frontend/.env.example
 - frontend/.env.local
 - frontend/app/globals.css
 - frontend/tailwind.config.ts
 - frontend/lib/api-client.ts
 - frontend/lib/types.ts
 - frontend/components/providers/theme-provider.tsx
 - frontend/components/layout/theme-toggle.tsx
 - frontend/components/layout/site-header.tsx
 - frontend/app/(app)/layout.tsx
 - frontend/app/layout.tsx
 - frontend/app/(auth)/layout.tsx
 - frontend/app/(auth)/login/page.tsx
 - frontend/app/(auth)/register/page.tsx
 - frontend/middleware.ts
 - frontend/.eslintrc.json
 - frontend/components/ui/button.tsx
 - frontend/components/ui/input.tsx
 - frontend/components/ui/label.tsx
 - frontend/components/ui/form.tsx
 - frontend/components/ui/card.tsx
 - frontend/components/ui/dropdown-menu.tsx
 - frontend/components/ui/sonner.tsx
 - frontend/components/ui/separator.tsx
 - specs/001-video-generation/tasks.md
tests:
 - npm run build (frontend) — pass
 - npm run lint (frontend) — pass
 - manual: register → login → session/CSRF cookies via /api proxy → GET /me → logout → session invalidated (curl)
 - manual: Playwright screenshots of /login, /register (dark+light, desktop+mobile 375px) and authenticated header/logout flow
---

## Prompt

Implement the REMAINING Phase 2 (Foundational) tasks from specs/001-video-generation/tasks.md: T031a (if still open) and ALL frontend Phase 2 tasks — design tokens (globals.css + tailwind.config.ts per design-system.md, light + dark, Inter + Noto Nastaliq Urdu, `.urdu` utility), Next.js /api rewrites to the backend, api-client with CSRF header, theme provider, root layout with Toaster, the shared app header (logo, Create, My Videos, theme toggle, Logout), login + register pages, and the auth middleware.

Notes:
- shadcn/ui is already initialized (components.json, New York style, Tailwind v3). Add needed shadcn components with `npx shadcn@2.3.0 add <name>`. Keep shadcn token names but replace their values with design-system.md values.
- Backend runs with: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload (port 8000). frontend/.env.local already exists.
- Premium look: follow design-system.md exactly (dark-first, violet→teal accent, no hard-coded colors). Login/register should look like a polished product, not a default template.

After coding: run `npm run build` and `npm run lint` in frontend and fix all errors. Start both servers and confirm register → login → header shows → logout works through the /api proxy. Mark completed tasks [X]. Stop and report: files created, build/lint result, and the commands to start the frontend.

## Response snapshot

Implemented all remaining Phase 2 tasks (T031a, T032, T033, T033a–T033d, T034–T037):

- **T031a**: `next.config.ts` rewrites `/api/:path*` → `BACKEND_ORIGIN` (default `http://127.0.0.1:8000`); `.env.example`/`.env.local` carry `NEXT_PUBLIC_API_BASE_URL=/api` + new `BACKEND_ORIGIN` var.
- **T033a**: Full design-system.md token set in `globals.css` as HSL custom properties (dark `:root` default, `.light` override), converted from the spec's hex values; mobile-first typography scale via CSS vars swapped at a `768px` media query (so a single `text-display`/`text-urdu`/etc. Tailwind utility is responsive without duplicating classes); `.urdu` utility (`dir:rtl`, Noto Nastaliq font, loose line-height); `.shadow-raised` elevation recipe per theme; gradient tokens kept as raw hex for `linear-gradient()`. `tailwind.config.ts` maps shadcn's token names to these vars and adds `success`/`warning` and the `display/h1/h2/h3/body/body-sm/urdu-script` font-size scale; removed the unused chart/sidebar tokens from the shadcn-generated default.
- **T032**: `lib/api-client.ts` — typed `apiClient.get/post/put/patch/delete`, `credentials:'include'`, reads the `csrf_token` cookie into `X-CSRF-Token` on unsafe methods, throws `ApiError` parsed from the backend's `{error:{code,message,requestId,resetsAt}}` shape.
- **T033/T033b/T033c/T033d**: `ThemeProvider` (next-themes, `attribute="class"`, `defaultTheme="system"`); `ThemeToggle` (dropdown, light/dark/system); `SiteHeader` (`variant: 'authenticated'|'anonymous'` prop — Phase 2 only wires the authenticated variant via `(app)/layout.tsx`; anonymous variant is ready for Phase 6's landing page reuse) with logo, Create/My Videos links, logout (`POST /auth/logout` + redirect), theme toggle.
- **T034**: root `layout.tsx` — Inter + Noto Nastaliq Urdu via `next/font/google` feeding `--font-inter`/`--font-urdu`, `ThemeProvider`, shadcn `Toaster` (sonner).
- **T035/T036**: Login/register pages — react-hook-form + zod, shadcn `Form`/`Card`, gradient CTA button, toast on `ApiError`, redirect to `/create` on success. Added an `(auth)` layout shell (logo + theme toggle + soft gradient glow) for a polished shared shell, not itself a numbered task but implied by "premium look."
- **T037**: `middleware.ts` — redirects to `/login?next=<path>` when the `session_id` cookie is absent, matcher covers `/create`, `/review`, `/videos`, `/videos/:path*`.

Also ran `npx shadcn@2.3.0 add button input label form card dropdown-menu sonner separator` to scaffold the needed primitives, and fixed `.eslintrc.json` (added `next/typescript` to `extends` — the custom `@typescript-eslint/no-unused-vars` rule otherwise fails because `eslint-config-next`'s base config only registers the TS *parser*, not the plugin namespace, for bare `.eslintrc.json` users).

Verified with the backend (`uvicorn`, port 8000, against the already-running dev Postgres/Redis) and frontend (`next dev`, port 3000) both live: `npm run build` and `npm run lint` both pass clean; curl-based cookie-jar test confirmed register → first-party `session_id`+`csrf_token` cookies → authenticated `GET /me` → CSRF-protected `POST /auth/logout` (204) → session invalidated (401) → re-login, all through the `/api` rewrite. Playwright (chromium, manually pointed at an already-cached browser binary since sandboxed `apt`/sudo blocked `--with-deps`) confirmed the dark/light visual design, 375px mobile layout with no horizontal scroll, and the authenticated header (logo, Create/My Videos, theme toggle, Logout) rendering and working against a temporary scratch route that was deleted immediately after the check (no Phase 3 page exists yet, so `/create` itself 404s as expected — that page is a separate, later task).

All 11 remaining Phase 2 checkboxes in `tasks.md` marked `[X]`. Dev servers stopped at the end of the session.

## Outcome

- ✅ Impact: Phase 2 (Foundational) is now fully complete on the frontend side — every subsequent Phase 3+ page can build on working design tokens, same-origin API wiring, auth pages, the shared header, and route protection.
- 🧪 Tests: `npm run build` pass, `npm run lint` pass, manual curl auth-flow pass, manual Playwright visual/interaction pass (all ad hoc — Phase 2 has no automated frontend test tasks per the constitution's 3-critical-path test scope).
- 📁 Files: see `files:` front matter above — 23 frontend files created/modified, `.eslintrc.json` fixed, `tasks.md` checkboxes updated.
- 🔁 Next prompts: Phase 3 (User Story 1) — Create/Review/Progress pages, script generation, mock video pipeline.
- 🧠 Reflection: the design-system.md "mobile value vs. desktop value" typography spec doesn't map cleanly onto a single Tailwind utility without either duplicating classes per breakpoint or swapping the underlying CSS variable at a media query — chose the latter so every component gets one `text-display`-style class that is already responsive, matching design-system.md's "mobile-first, enhanced at `md:`" rule.

## Evaluation notes (flywheel)

- Failure modes observed: the project's own `.eslintrc.json` referenced `@typescript-eslint/no-unused-vars` without extending a config that registers that plugin — `next/core-web-vitals` alone only wires the TS *parser* for `.ts(x)` files, not the plugin namespace, so `next build`'s lint step failed on every file until `next/typescript` was added to `extends`.
- Graders run and results (PASS/FAIL): build PASS, lint PASS, manual auth-flow curl PASS, manual Playwright visual/flow check PASS.
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): n/a
