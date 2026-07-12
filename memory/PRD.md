# Expo Proxy — Unified Restaurant Revenue Engine

## Original Problem Statement
User has three TypeScript/Express repos (extracted from an "Expo Proxy" monorepo) forming
one closed-loop marketing system for local restaurants. Goal: turn them into ONE unified,
demoable, competition-ready web app that shows the complete loop, with external systems mocked.

## Vision / Positioning
A premium ($299/mo) **marketing REVENUE engine** — NOT a social media tool.
"Everyone else helps you look busy. This makes you money — and learns how every week."
Contrast anchor: beats Valpak ($750 blind blanket mail) with $299 targeted, measured, self-improving campaigns.

## The three integrated modules (faithfully ported to Python/FastAPI)
1. **Content Director** — asset vault, daily shooting prompts, speech→copy (GBP/FB/IG drafts),
   Brutal Honesty Video Critic (hook/audio/framing grades WEAK→STRONG with blunt fixes).
2. **AdSmith** — closed-loop weekly budget engine. Strategy A (Paid Local Velocity) vs
   Strategy B (Organic Community Outreach). Attributes orders via promo codes, computes
   revenue/ROAS/CAC/new customers + zip breakdown, shifts budget 70/30 toward ROAS winner,
   learns week over week (50/50 → 80/20). Interactive "Run Next Week" advances the loop.
3. **EchoLink** — segment-aware Scan-to-Spin (couponers get small reward, new/quality get
   high-value), RFMD VIP segmenting, POS verification layer (redeemed codes → revenue proof),
   30-day slow-trickle drip.

## Architecture
- Backend: FastAPI (`/app/backend/server.py`), engines as deterministic functions, seeded demo data (in-memory). Prefix `/api`.
- Frontend: React (CRA/craco), `@` alias → src. Sections in `src/sections/*`, api in `src/lib/api.js`.
- Design: `/app/design_guidelines.json` — Cormorant Garamond / Manrope / JetBrains Mono. Bone/Orange/Forest-Green. Money-first.

## MOCKED (not real integrations)
Google auth, n8n/Whisper transcription, real ad-platform posting/feeds, POS/platform data,
ordering-platform redirects. All realistic seeded data for a clickable demo.

## Implemented (2026-06/07)
- Full 4-section dashboard: Command Center, Content Director, AdSmith, EchoLink.
- Interactive: generate copy, grade sample videos, run-next-week loop, segment-aware spin.
- Verified: all sections render; backend endpoints return correct data.

## Business model (captured from user)
- $299/mo single unified package. Premium = feature.
- GTM: guided Zoom onboarding, 2-week free trial, results guarantee.
- Reseller army: 50/50 commission split for first 3 months (retention-aligned).

## Backlog / Next Action Items
- P1: Onboarding "asset vault capture" flow (film restaurant + evergreen pre-records) as the front door.
- P1: Two-lane orchestration (organic free vs paid targeted) with executable buttons + 2–3 week planner.
- P1: Platform click + button-conversion feed model (CSV as fallback, not front door).
- P2: Real integrations — Google auth, Meta/TikTok/Google Ads APIs, POS/ordering conversion tracking.
- P2: Persist to MongoDB; multi-restaurant (deployment-per-restaurant per ADR-001).
- P2: Tiered pricing ladder (content-only entry → full loop pro tier w/ EchoLink gating).
