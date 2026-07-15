# OmniLocal #1 — Unified Restaurant Revenue Engine

## Original Problem Statement
A single unified, demoable, competition-ready web app that shows a complete closed-loop
marketing system for local restaurants, with external systems mocked. Rebranded strictly to
**OmniLocal #1**. Tagline: *"This is your one and only revenue engine that you will ever need."*

## Strict Naming (do NOT reintroduce legacy names)
- Product: **OmniLocal #1**
- Modules: **Content Director**, **Quality Content Executioner** (Ad Engine),
  **Quality Customer Maximizer** (Rewards / Gamification).
- Legacy names permanently purged: AdSmith, ExpoProxy, EchoLink. Legacy test artifact
  `backend_test.py` deleted.

## The three integrated modules (Python/FastAPI, deterministic)
1. **Content Director** — asset vault, daily shooting prompts, speech→copy (GBP/FB/IG drafts),
   Brutal Honesty Video Critic, and **distribution pathways** (GBP, Facebook Reels, Instagram
   Reels, TikTok, YouTube Shorts).
2. **Quality Content Executioner** — closed-loop weekly budget engine (Strategy A vs B), promo-code
   attribution, ROAS/CAC learning loop, ZIP breakdown, connection-gated recommended plan.
3. **Quality Customer Maximizer** — 4 rotating games (30-day cycle, admin-toggleable), segment-aware
   Scan-to-Spin, RFMD VIP segmenting, weekly customer CSV import (new / coupon_only / loyal),
   welcome-video automation, 30-day slow-trickle drip.

## Social Media Connector (OAuth handshake)
- Unified API provider handshake, **stubbed until `UNIFIED_API_KEY` set**.
- Routes: `GET /api/connections/pathways`, `GET /api/connections/oauth/{platform}/start`,
  `POST /api/connections/oauth/callback`, `GET/PUT /api/connections`.
- UI exposes a clear **Connect** flow during onboarding (Connections, embedded under the Ad Engine).

## Email Engine (Anti-Spam Trickle) — Resend, STUBBED
- Sending stubbed until `RESEND_API_KEY` provided.
- Mandatory: 15-second throttle between sends, `Reply-To` + `List-Unsubscribe` headers,
  content sanitization (spam-phrase/all-caps/tracking-pixel checks).
- Welcome automation: new customers → automated email with static owner welcome video URL.

## Architecture
- Backend: FastAPI (`/app/backend/server.py`), deterministic engines, seeded in-memory data. Prefix `/api`.
- Frontend: React (CRA/craco), `@` alias → src. Sections in `src/sections/*`, api in `src/lib/api.js`.
  Nav: Command Center, Quality Content Executioner, Quality Customer Maximizer, Content Director.

## MOCKED (not real integrations)
Google auth, transcription, real ad-platform posting/feeds, POS/platform data, ordering redirects,
Resend sending, Unified social OAuth. All realistic seeded data for a clickable demo.

## Implemented (2026-06)
- Full rebrand to OmniLocal #1; legacy strings + `backend_test.py` purged.
- 4 rotating games, weekly CSV segmentation, welcome-video automation, anti-spam trickle engine.
- Social Media Connector OAuth handshake (start/callback, stubbed) + Connect flow UI.
- Distribution pathways defined in Content Director backend + surfaced in UI.

## Backlog / Next Action Items
- P1: Activate real Resend sending once `RESEND_API_KEY` provided (un-stub `send_via_resend`).
- P1: Activate live Unified social OAuth once `UNIFIED_API_KEY` provided.
- P1: "Film-once onboarding vault" capture flow feeding the Content Director.
- P2: Real OAuth into Meta/Google/TikTok/YouTube for automated spend.
- P2: Persist in-memory data (games, segments, reports, connections) to MongoDB.
- P2: Refactor `server.py` into modular routers as integrations grow.
