# Design System: Student Video Generation

Distilled from the competitor UI research in `research.md` (Section B). This
defines tokens and a component list for `frontend/` using Tailwind CSS +
shadcn/ui. Dark-first, equally-polished light mode, mobile-first responsive,
per the constitution's UI standard. No logos, brand names, or assets from any
researched product are reused — patterns only.

## Design Principles

1. **Dark-first, premium** — default theme is dark (matches category
   convention: Runway, Higgsfield), signaling a serious creative tool rather
   than a consumer toy. Light mode is a fully-designed peer, not a fallback.
2. **Show the step, not just a spinner** — every long-running action (script
   generation, video processing) shows a labeled current step, matching every
   researched tool's progress UI convention.
3. **Quantized choices, not sliders** — duration, aspect ratio, and voice are
   always discrete visual cards (matches Kling/Luma/Runway Gen-3/Hailuo
   convention for duration & aspect ratio), never a free-form input.
4. **RTL Urdu is a first-class citizen**, not a special case bolted onto an
   LTR layout — script/narration text blocks get their own RTL-aware
   container with proper line-height for Nastaliq script's vertical stacking.

## Color Tokens

Expressed as CSS custom properties consumed by Tailwind (`tailwind.config`
`extend.colors` mapped to `var(--token)`), following shadcn/ui's token
convention (`background`, `foreground`, `primary`, etc.) so shadcn components
need no per-component overrides.

### Dark (default)

| Token | Value | Usage |
|---|---|---|
| `--background` | `#0A0A0F` | App background — near-black, slight blue cast |
| `--surface` | `#15151D` | Cards, panels |
| `--surface-raised` | `#1E1E29` | Modals, popovers, option-card hover |
| `--foreground` | `#F4F4F6` | Primary text |
| `--muted-foreground` | `#9A9AA8` | Secondary text, captions |
| `--border` | `#2A2A36` | Dividers, card borders |
| `--primary` | `#7C5CFF` | Primary CTA (violet — distinct from any researched brand's signature color) |
| `--primary-foreground` | `#FFFFFF` | Text on primary |
| `--accent-gradient-from` | `#7C5CFF` | Hero/CTA gradient start |
| `--accent-gradient-to` | `#00D1C7` | Hero/CTA gradient end (violet → teal) |
| `--success` | `#2ED47A` | "Ready" status badge |
| `--warning` | `#F5A524` | "Processing" status badge |
| `--destructive` | `#F5484B` | "Failed" status badge, destructive actions |
| `--ring` | `#7C5CFF` | Focus ring |

### Light

| Token | Value | Usage |
|---|---|---|
| `--background` | `#FFFFFF` | App background |
| `--surface` | `#F7F7FB` | Cards, panels |
| `--surface-raised` | `#FFFFFF` (with shadow) | Modals, popovers |
| `--foreground` | `#13131A` | Primary text |
| `--muted-foreground` | `#63636F` | Secondary text |
| `--border` | `#E4E4ED` | Dividers, card borders |
| `--primary` | `#6A42F2` | Primary CTA (slightly deepened for AA contrast on white) |
| `--primary-foreground` | `#FFFFFF` | Text on primary |
| `--accent-gradient-from` | `#6A42F2` | Hero/CTA gradient start |
| `--accent-gradient-to` | `#00A89F` | Hero/CTA gradient end |
| `--success` | `#188A4B` | "Ready" badge (AA on white) |
| `--warning` | `#B5700A` | "Processing" badge |
| `--destructive` | `#D1343A` | "Failed" badge, destructive actions |
| `--ring` | `#6A42F2` | Focus ring |

All pairings must meet WCAG AA (4.5:1 body text, 3:1 large text) in both modes
— verify `foreground`/`muted-foreground` against `background`/`surface` when
implementing.

## Typography

- **UI font (English)**: Inter (via `next/font/google`), weights 400/500/600/700.
- **Urdu font**: **Noto Nastaliq Urdu** (via `next/font/google`), used for
  every rendering of `correctedIdea`, `urduScript`, and scene text in Urdu.
  Nastaliq needs more line-height than Latin text to avoid clipping descenders
  — set `line-height: 2` (not Tailwind's default `leading-normal`) on any
  container using this font, and `dir="rtl"` on the element, not just
  `text-align: right` (so cursor/selection behavior is correct in editable
  fields on the Review screen).

| Scale | Size / Line-height | Usage |
|---|---|---|
| `display` | 48px/56px (mobile: 32px/40px) | Landing hero headline |
| `h1` | 32px/40px (mobile: 24px/32px) | Page titles (Create, My Videos) |
| `h2` | 24px/32px | Section headings |
| `h3` | 18px/28px | Card titles |
| `body` | 16px/24px | Default body text |
| `body-sm` | 14px/20px | Captions, metadata (dates, status) |
| `urdu-script` | 20px/40px (mobile: 18px/36px) | Review screen script/narration text — intentionally larger and looser than `body` for Nastaliq legibility |

## Spacing & Radius

- Spacing scale: Tailwind defaults (4px base unit), no custom scale needed —
  avoids inventing a parallel system (Principle I).
- Radius: `--radius-sm: 8px` (inputs, badges), `--radius-md: 12px` (cards),
  `--radius-lg: 20px` (hero media, modals). Option cards (duration/aspect
  ratio/voice) use `--radius-md`.

## Shadows & Elevation

- Dark mode: shadows read as a subtle lighter-border + glow rather than a
  black drop-shadow (which is invisible on near-black backgrounds):
  `box-shadow: 0 0 0 1px var(--border), 0 8px 24px -8px rgb(124 92 255 / 0.25)`
  on raised/hovered surfaces.
- Light mode: conventional soft shadow:
  `box-shadow: 0 1px 2px rgb(0 0 0 / 0.04), 0 8px 24px -8px rgb(0 0 0 / 0.08)`.

## Motion

- Durations: 150ms (micro — hover/focus), 250ms (standard — panel/modal
  enter), 400ms (hero/emphasis — autoplay video fade-in).
- Easing: `ease-out` for entrances, `ease-in` for exits — no custom bezier
  curves needed.
- Progress stepper: each step transitions with a 250ms fade+slide when it
  becomes active; the active step's icon gets a subtle pulse (`animate-pulse`,
  Tailwind built-in) rather than a custom spinner graphic, keeping it simple
  and consistent across the step list.
- Respect `prefers-reduced-motion`: disable the hero autoplay video's
  motion-heavy entrance and the pulse animation, falling back to instant
  state changes.

## Component List (shadcn/ui-based)

| Component | shadcn/ui base | Notes |
|---|---|---|
| Option Card (duration / aspect ratio / voice) | `Card` + `RadioGroup` (visually restyled as cards, not radio dots) | Selected state uses `--primary` border + subtle glow; one shared component, parameterized by icon + label + value |
| Idea Textarea | `Textarea` + custom char counter | Shows `n/500` live; red state under 10 or over 500 |
| Word Counter (Review screen) | Custom, built on `Badge` | Shows `word_count / word_limit`; switches to `--destructive` styling and disables Approve button when over limit (FR-010) |
| Progress Stepper | Custom (no direct shadcn primitive) | Horizontal on desktop, vertical on mobile; steps: Preparing → Generating scenes (1/N) → Adding voice → Finalizing → Ready |
| Status Badge | `Badge` | Variant per status: Processing (warning), Ready (success), Failed (destructive) |
| Video Card (My Videos grid) | `Card` + `AspectRatio` | Thumbnail with hover-autoplay preview (muted, looped) matching Pika/Higgsfield gallery convention; overlay play/download/delete icon buttons on hover (desktop) or always-visible (mobile) |
| Theme Toggle | `DropdownMenu` or simple icon `Button` | Light/Dark/System, persisted via `next-themes` |
| Auth Forms (login/register/forgot/reset) | `Form` (react-hook-form + zod resolver) + `Input` + `Button` | Shared layout shell for all four auth routes |
| Toast / Error Banner | `Toast` (sonner, shadcn's recommended toast) | All friendly error messages (FR-033) surface here, never inline stack traces |
| FAQ Accordion | `Accordion` | Public landing page |
| Showcase Grid | `Card` + `AspectRatio` | Public landing page sample-video grid, same visual language as My Videos' Video Card |

## Responsive Rules

- Mobile-first breakpoints: base (< 640px) is the design target first;
  `sm:`/`md:`/`lg:` Tailwind prefixes add desktop enhancements, never the
  reverse.
- Option cards (duration/aspect ratio/voice): horizontal scroll-snap row on
  mobile, grid on `md:` and up.
- Progress Stepper: vertical list on mobile (each step full-width), horizontal
  with connecting line on `md:` and up.
- My Videos / Showcase grids: 1 column (mobile) → 2 (`sm:`) → 3 (`md:`) → 4
  (`lg:`) columns.
