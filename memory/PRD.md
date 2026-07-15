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
- Full 6-section dashboard: Command Center, Content Director, AdSmith, EchoLink, Codes & Redemption, Connections.
- Interactive: generate copy, grade sample videos, run-next-week loop (seeded 3 weeks → visible shift), segment-aware spin.
- Weekly Code System (Codes): configurable length (4/8/10/11) for any POS, probability-weighted reward tiers, multiple interchangeable variant codes per tier, weekly expiry/rotation, CSV reconciliation (flags invalid/expired, computes redemption rate + proven revenue). POS-agnostic, no API needed.
- Platform Connection Toggles (Connections): per-platform on/off; AdSmith "Recommended Plan" GATED to connected channels only (unconnected struck-through). Diversification nudge + pre-Zoom setup guide.
- Verified: all sections render; endpoints + interactive flows confirmed via curl + screenshots.

## Business model (captured from user)
- $299/mo single unified package. Premium = feature.
- GTM: guided Zoom onboarding, 2-week free trial, results guarantee.
- Reseller army: 50/50 commission split for first 3 months (retention-aligned).

## Backlog / Next Action Items
- P1: Onboarding "asset vault capture" flow (film restaurant + evergreen pre-records) as the front door.
- P1: Two-lane orchestration (organic free vs paid targeted) with executable buttons + 2–3 week planner.
- P2: Real integrations — transcription (Whisper, available now) → OAuth into Meta/Google/TikTok (read+post) → Marketing APIs (automated spend).
- P2: Persist connections/codes/reports to MongoDB; multi-restaurant (deployment-per-restaurant per ADR-001).
- P2: Wire code-reconciliation results into AdSmith's live learning loop (currently seeded).
- P2: Tiered pricing ladder (content-only entry → full loop pro tier w/ EchoLink gating).
