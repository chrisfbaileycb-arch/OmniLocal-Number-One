"""
OmniLocal #1 — Unified Restaurant Revenue Engine (demo backend).

Faithfully ports the deterministic engines from the three source repos:
  - Content Director : shooting prompts, transcript->copy, Brutal Honesty Critic
  - Quality Content Executioner : closed-loop weekly budget allocation + A/B learning
  - Quality Customer Maximizer   : rotating games, RFMD VIP segmenting, slow-trickle drip

External systems (Google auth, n8n/Whisper transcription, real ad posting,
POS/platform feeds) are MOCKED with realistic seeded data so the full loop is
clickable end-to-end. Money-first: revenue and ROAS lead every response.
"""

from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import re
import random
import asyncio
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="OmniLocal #1 Revenue Engine")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("omnilocal")

# ---------------------------------------------------------------------------
# Demo restaurant brand
# ---------------------------------------------------------------------------
BRAND = {
    "name": "Nonna's Corner Deli",
    "city": "Springfield",
    "signatureItem": "The Sunday Gravy Sub",
    "igHandle": "nonnascorner",
    "orderUrl": "https://order.nonnascorner.com",
}

# ===========================================================================
# CONTENT DIRECTOR — shooting prompts
# ===========================================================================
SHOOTING_PROMPTS = [
    {"id": "ingredient-story", "title": "Ingredient Story",
     "prompt": "Pick up the most interesting ingredient in your kitchen right now and tell us where it comes from — farm, supplier, region, or family connection.",
     "guidance": "Hold the ingredient in frame. Lead with the name before any backstory. Keep it under 60 seconds."},
    {"id": "operational-hustle", "title": "Operational Hustle",
     "prompt": "Walk us through one thing that happens before we open that customers never see — the prep, the ritual, the grind.",
     "guidance": "Film the actual action while you talk. Fast-moving hands read best on mobile."},
    {"id": "behind-the-counter-secret", "title": "Behind-the-Counter Secret",
     "prompt": "Share one technique, ratio, or decision that makes your dish different — something a regular might never guess.",
     "guidance": "Be specific: a temperature, a time, a tool. Vague secrets get skipped."},
    {"id": "community-gratitude", "title": "Community Gratitude",
     "prompt": "Thank a specific corner of your community — a supplier, a neighboring business, or the regulars who kept you open.",
     "guidance": "Name the person or business. Generic 'thanks everyone' posts underperform by 40% vs named shout-outs."},
    {"id": "demographic-pivot", "title": "Demographic Pivot",
     "prompt": "Describe one way you adapted a menu item or your hours to better serve a group in your neighborhood that others overlook.",
     "guidance": "Lead with the community, then the change. Avoid generalizations — be hyper-local."},
    {"id": "menu-focus", "title": "Menu Focus",
     "prompt": "Pick your single best-seller this week and explain — in one sentence — why a first-time guest should order it.",
     "guidance": "Say the item name in the first three seconds. Sell the outcome, not the process."},
    {"id": "staff-spotlight", "title": "Staff Spotlight",
     "prompt": "Introduce one team member: their name, how long they've been here, and one thing they do better than anyone else.",
     "guidance": "Get the team member on camera. Authenticity beats polish — a candid laugh outperforms a rehearsed line."},
    {"id": "honest-entrepreneur", "title": "Honest Entrepreneur",
     "prompt": "Share one genuine challenge you faced this month — a supplier issue, a slow week, a lesson learned — and how you moved through it.",
     "guidance": "Vulnerability is the hook. Let the struggle breathe for at least ten seconds."},
]


def daily_prompt(date_str: str) -> dict:
    h = 0
    for ch in date_str:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return SHOOTING_PROMPTS[h % len(SHOOTING_PROMPTS)]


# ===========================================================================
# CONTENT DIRECTOR — transcript normalizer + copywriter
# ===========================================================================
STANDALONE_FILLERS = ["you know what i mean", "you know", "i mean", "so yeah",
                      "um", "uh", "hmm", "hm", "er", "ah"]
STOP_WORDS = set(
    "a an the and or but in on at to for of with by from up about into through during is was are were "
    "be been being have has had do does did will would could should may might shall can it its this that "
    "these those i me my we our you your he him his she her they them their what which who whom how when "
    "where why all each every both few more most other some such no not only same so than too very just "
    "because as until while if then get got go going make made take took come came say said know think "
    "thought see saw really also".split()
)


def normalize_transcript(verbatim: str) -> str:
    if not verbatim or not verbatim.strip():
        return ""
    text = verbatim
    for phrase in STANDALONE_FILLERS:
        text = re.sub(r"(?:,\s*|\s+|^)" + re.escape(phrase) + r"(?:\s*,|\s+|(?=[,.!?;:])|\s*$)",
                      " ", text, flags=re.IGNORECASE)
    text = re.sub(r",\s*like\s*,", ",", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\w+)((?:[,\s]+\1\b)+)", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*,\s*,", ",", text)
    text = re.sub(r"\s+([.!?;:,])", r"\1", text)
    return text.strip()


def _key_phrases(text: str, n: int = 5):
    tokens = re.sub(r"[^a-z0-9'\s-]", " ", text.lower()).split()
    phrases, run = [], []
    for tok in tokens:
        if tok not in STOP_WORDS and len(tok) > 2:
            run.append(tok)
        else:
            if len(run) >= 2:
                phrases.append(" ".join(run))
            elif len(run) == 1:
                phrases.append(run[0])
            run = []
    if len(run) >= 2:
        phrases.append(" ".join(run))
    elif len(run) == 1:
        phrases.append(run[0])
    seen, out = set(), []
    for p in sorted(phrases, key=len, reverse=True):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out[:n]


def _cap(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


def draft_posts(normalized: str) -> dict:
    kp = _key_phrases(normalized)
    top = _cap(kp[0]) if kp else _cap(BRAND["signatureItem"])
    city, name, item = BRAND["city"], BRAND["name"], BRAND["signatureItem"]
    second = f" {_cap(kp[1])}." if len(kp) > 1 else ""
    gbp = (f"{city} {item} done right — {top}.{second} Visit {name} for an authentic "
           f"{city} experience. Order Online: {BRAND['orderUrl']}")
    m = re.match(r"^[^.!?]+[.!?]", normalized)
    hook = m.group(0).strip() if m else normalized[:120].strip()
    detail = ", ".join(_cap(x) for x in kp[1:3])
    detail_line = f" {detail} — that's what we're about." if detail else ""
    fb = (f"{hook}{detail_line}\n\nOur neighbors know what we're made of. At {name}, every "
          f"visit is a little piece of {city} at its best.\n\nWhat's your go-to order? Drop it below!")
    slug = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    tags = " ".join([f"#{slug(city)}eats", f"#{slug(city)}food", f"#{slug(item)}",
                     "#foodie", "#supportlocal", "#restaurantlife"])
    ig = f"{top}.\n{item} in {city}.\nThis is why you stop in.\n\nOrder via link in bio.\n\n{tags}\n@{BRAND['igHandle']}"
    return {"gbp": gbp, "facebook": fb, "instagram": ig}


# ===========================================================================
# CONTENT DIRECTOR — Brutal Honesty Video Critic
# ===========================================================================
GRADE_RANK = {"WEAK": 0, "MODERATE": 1, "IMPROVABLE": 2, "STRONG": 3}


def _score_hook(h):
    if not h["startsWithAction"] or h["secondsBeforeSubject"] > 2:
        secs = int(h["secondsBeforeSubject"]) + 1
        return {"grade": "WEAK",
                "critique": f'Your hook does not grab attention. "{h["firstWords"]}" is not an action opener — viewers scroll past in under 2 seconds.',
                "recommendation": f"Cut the first {secs}s. Start mid-action or lead with the single most interesting word. The subject must appear within 2 seconds."}
    if h["secondsBeforeSubject"] > 1:
        return {"grade": "IMPROVABLE",
                "critique": f'Action opener detected but the subject arrives at {h["secondsBeforeSubject"]:.1f}s — borderline. Some of your audience will drop off.',
                "recommendation": "Trim the opening by half a second so the subject is visible immediately after the action word."}
    return {"grade": "STRONG", "critique": "Hook opens with action and subject is on screen within 1 second. This is correct.",
            "recommendation": "Maintain this pattern on every clip."}


def _score_audio(a):
    snr = a["avgLoudnessDb"] - a["backgroundNoiseDb"]
    if snr <= 10:
        return {"grade": "MODERATE",
                "critique": f"Background noise ({a['backgroundNoiseDb']} dBFS) is within {snr:.0f} dB of your voice. Likely culprit: an exhaust fan or kitchen equipment nearby.",
                "recommendation": "Turn off the exhaust fan while filming, or move 10 feet away. Noise ruins perceived production value."}
    if a["energy"] == "flat":
        return {"grade": "IMPROVABLE", "critique": "Audio energy is flat. Your delivery sounds monotone, which loses viewers even when the content is good.",
                "recommendation": "Add vocal variation: speed up on exciting details, pause before key words, let enthusiasm into your voice."}
    return {"grade": "STRONG", "critique": "Voice is clearly above background noise and energy is readable. Audio passes.",
            "recommendation": "Keep the exhaust off during filming and maintain this energy level."}


def _score_framing(f):
    if f["subjectLit"] == "back":
        return {"grade": "IMPROVABLE", "critique": "You are back-lit. The camera sees the bright window behind you, turning your face into a silhouette.",
                "recommendation": "Step toward the window light so it falls on your face. Natural front-lighting is free and looks professional."}
    if f["subjectCutOff"]:
        return {"grade": "WEAK", "critique": "Part of the subject is cut off frame. Viewers notice something is wrong even if they can't name it.",
                "recommendation": "Step back until the full subject — head to waist minimum — is in frame with a small buffer at each edge."}
    if f["clutterScore"] > 0.6:
        return {"grade": "MODERATE", "critique": f"Background clutter is {f['clutterScore']*100:.0f}% — too much visual noise competes with the subject.",
                "recommendation": "Clear a 3-foot zone behind you: move boxes, bins, or random equipment out of shot."}
    if f["subjectLit"] == "side":
        return {"grade": "IMPROVABLE", "critique": "Side lighting creates harsh shadows on half the face. Acceptable but not ideal for talking-head content.",
                "recommendation": "Rotate 45° toward the light source for a soft 3/4 front-light instead of a hard side split."}
    return {"grade": "STRONG", "critique": "Subject is front-lit, fully in frame, and the background is clean. Framing passes.",
            "recommendation": "Keep this setup as your default for all talking-head clips."}


def score_video(a: dict) -> dict:
    hook, audio, framing = _score_hook(a["hook"]), _score_audio(a["audio"]), _score_framing(a["framing"])
    overall = min([hook["grade"], audio["grade"], framing["grade"]], key=lambda g: GRADE_RANK[g])
    return {"filename": a["filename"], "hook": hook, "audio": audio, "framing": framing, "overall": overall}


SAMPLE_VIDEOS = [
    {"filename": "dinner-rush-sub.mov", "label": "Cook building the Sunday Gravy Sub (dinner rush)",
     "hook": {"startsWithAction": True, "firstWords": "Watch this", "secondsBeforeSubject": 0.8},
     "audio": {"avgLoudnessDb": -12, "backgroundNoiseDb": -34, "energy": "high"},
     "framing": {"subjectLit": "front", "subjectCutOff": False, "clutterScore": 0.2}},
    {"filename": "owner-intro.mov", "label": "Owner intro filmed by the front window",
     "hook": {"startsWithAction": False, "firstWords": "Um, hi everyone, so today", "secondsBeforeSubject": 4.5},
     "audio": {"avgLoudnessDb": -18, "backgroundNoiseDb": -24, "energy": "flat"},
     "framing": {"subjectLit": "back", "subjectCutOff": False, "clutterScore": 0.4}},
    {"filename": "menu-tour.mov", "label": "Quick menu tour behind the counter",
     "hook": {"startsWithAction": True, "firstWords": "Here's the special", "secondsBeforeSubject": 1.4},
     "audio": {"avgLoudnessDb": -14, "backgroundNoiseDb": -30, "energy": "moderate"},
     "framing": {"subjectLit": "side", "subjectCutOff": True, "clutterScore": 0.7}},
]

ASSET_VAULT = [
    {"id": "av1", "title": "Chef plating during service", "category": "Signature Prep", "clips": 12},
    {"id": "av2", "title": "Fresh dough at 6am", "category": "Operational Hustle", "clips": 8},
    {"id": "av3", "title": "Regulars at the counter", "category": "Community", "clips": 15},
    {"id": "av4", "title": "Happy Birthday evergreen", "category": "Evergreen / Holidays", "clips": 5},
    {"id": "av5", "title": "Thanksgiving thank-you", "category": "Evergreen / Holidays", "clips": 4},
    {"id": "av6", "title": "The Sunday Gravy Sub build", "category": "Hero Product", "clips": 9},
]

# ===========================================================================
# QUALITY CONTENT EXECUTIONER — strategies + closed-loop budget engine
# ===========================================================================
STRATEGY_A = {"id": "A", "displayName": "Paid Local Velocity", "prefix": "STRATA",
              "channels": ["facebook_act_now_ads", "google_maps_pin_boost"]}
STRATEGY_B = {"id": "B", "displayName": "Organic Community Outreach", "prefix": "STRATB",
              "channels": ["gbp_organic_boost", "local_story_drip"]}
CHANNEL_LABELS = {
    "facebook_act_now_ads": "Facebook Act-Now Ads", "google_maps_pin_boost": "Google Maps Pin Boost",
    "gbp_organic_boost": "Google Business Profile", "local_story_drip": "Local Story Drip (Reels)",
}
WEEKLY_BUDGET = 299.0


def _round(n):
    return round(n + 1e-9, 2)


def _split(channels, dollars):
    c = len(channels)
    base = round(dollars / c, 2)
    alloc = {}
    running = 0.0
    for i, ch in enumerate(channels):
        if i == c - 1:
            alloc[ch] = _round(dollars - running)
        else:
            alloc[ch] = base
            running += base
    return alloc


def _strategy_alloc(share, total, channels):
    dollars = _round(share * total)
    return {"share": share, "dollars": dollars, "perChannel": _split(channels, dollars)}


def build_allocation(week_of, share_a, total=WEEKLY_BUDGET):
    return {"weekOf": week_of, "totalBudget": total,
            "strategyA": _strategy_alloc(share_a, total, STRATEGY_A["channels"]),
            "strategyB": _strategy_alloc(_round(1 - share_a), total, STRATEGY_B["channels"])}


def _metrics(txs, prefix, spend):
    attributed = [t for t in txs if (t.get("promo_code") or "").startswith(prefix)]
    customers = {t["customer_id"] for t in attributed if t.get("customer_id")}
    revenue = _round(sum(t["net_sales"] for t in attributed))
    new_customers = len(customers)
    cac = _round(spend / new_customers) if new_customers else None
    roas = _round(revenue / spend) if spend else 0
    clicks = sum(t.get("clicks", 0) for t in attributed) or len(attributed) * 14
    conversions = len(attributed)
    return {"newCustomers": new_customers, "revenue": revenue, "cac": cac,
            "roas": roas, "clicks": clicks, "conversions": conversions, "spend": spend}


def _zip_breakdown(txs):
    m = {}
    for t in txs:
        z = t.get("postal_code")
        if not z:
            continue
        m.setdefault(z, {"customers": 0, "revenue": 0.0})
        if t.get("customer_id"):
            m[z]["customers"] += 1
        m[z]["revenue"] = _round(m[z]["revenue"] + t["net_sales"])
    return m


def _decide(ma, mb):
    if ma["cac"] is None and mb["cac"] is None:
        return {"winner": "tie", "winnerShare": 0.5}
    if ma["cac"] is None:
        return {"winner": "B", "winnerShare": 0.7}
    if mb["cac"] is None:
        return {"winner": "A", "winnerShare": 0.7}
    return {"winner": "A" if ma["roas"] >= mb["roas"] else "B", "winnerShare": 0.7}


# ---- deterministic seeded demo transactions per week -----------------------
def _seed_week_txs(week_index, share_a):
    """Generate believable POS/platform-attributed orders for one week.
    Strategy A (paid) trends to a higher ROAS, so the loop learns to favor it."""
    rng = random.Random(1000 + week_index)
    zips = ["01103", "01104", "01108", "01109", "01118"]
    txs = []
    spend_a = share_a * WEEKLY_BUDGET
    spend_b = (1 - share_a) * WEEKLY_BUDGET
    # paid converts harder as budget concentrates; add mild weekly lift (learning)
    a_orders = int(spend_a / 4.4) + week_index
    b_orders = int(spend_b / 7.2)
    for i in range(a_orders):
        txs.append({"promo_code": f"STRATA-{rng.randint(1000,9999)}",
                    "customer_id": f"A{week_index}-{i}",
                    "net_sales": _round(rng.uniform(16, 42)),
                    "postal_code": rng.choice(zips),
                    "clicks": rng.randint(8, 24),
                    "discounts_applied": rng.choice([0, 0, 0, 5])})
    for i in range(b_orders):
        txs.append({"promo_code": f"STRATB-{rng.randint(1000,9999)}",
                    "customer_id": f"B{week_index}-{i}",
                    "net_sales": _round(rng.uniform(12, 30)),
                    "postal_code": rng.choice(zips),
                    "clicks": rng.randint(4, 12),
                    "discounts_applied": rng.choice([0, 0, 5])})
    return txs, _round(spend_a), _round(spend_b)


def _monday(offset_weeks=0):
    d = datetime.now(timezone.utc)
    monday = d - timedelta(days=d.weekday()) + timedelta(weeks=offset_weeks)
    return monday.strftime("%Y-%m-%d")


def build_reports_history(num_weeks=5):
    """Run the closed loop across several weeks, starting 50/50 and learning."""
    reports = []
    share_a = 0.5
    for w in range(num_weeks):
        week_of = _monday(-(num_weeks - 1 - w))
        txs, spend_a, spend_b = _seed_week_txs(w, share_a)
        alloc = build_allocation(week_of, share_a)
        ma = _metrics(txs, "STRATA", alloc["strategyA"]["dollars"])
        mb = _metrics(txs, "STRATB", alloc["strategyB"]["dollars"])
        decision = _decide(ma, mb)
        reports.append({
            "weekOf": week_of, "allocation": alloc,
            "metrics": {"strategyA": ma, "strategyB": mb},
            "decision": decision, "zipBreakdown": _zip_breakdown(txs),
            "totalRevenue": _round(ma["revenue"] + mb["revenue"]),
            "totalSpend": alloc["totalBudget"],
            "blendedRoas": _round((ma["revenue"] + mb["revenue"]) / alloc["totalBudget"]),
        })
        # learn: shift toward winner (bounded so it stays believable)
        if decision["winner"] == "A":
            share_a = min(0.8, _round(share_a + 0.075))
        elif decision["winner"] == "B":
            share_a = max(0.2, _round(share_a - 0.075))
    return reports


# In-memory report store (seeded); reconcile appends the next learned week.
INITIAL_WEEKS = 3
REPORTS: List[dict] = build_reports_history(INITIAL_WEEKS)


# ===========================================================================
# QUALITY CUSTOMER MAXIMIZER — odds, RFMD, drip
# ===========================================================================
def spin(is_new_guest: bool, segment: str = "new"):
    """Segment-aware Scan-to-Spin.
    new / quality (vip)  -> high-value reward most of the time (entice them in)
    couponer (promo_pool) -> small reward most of the time (protect margin, CAC)
    repeat/standard       -> standard reward most of the time (sustainable)
    """
    rng = random.Random()
    if segment == "promo_pool":
        high = 0.05          # couponers rarely win big — protects your margin
        high_reward, std_reward = "Free Sub (BOGO)", "Free Fountain Drink"
    elif segment == "vip" or is_new_guest:
        high = 0.8           # new + quality guests: entice with the big reward
        high_reward, std_reward = "Free Sub (BOGO)", "20% Off Your Order"
    else:
        high = 0.1           # ordinary repeat: sustainable standard reward
        high_reward, std_reward = "Free Sub (BOGO)", "10% Off"
    tier = "highValue" if rng.random() < high else "standard"
    prefix = "HV-" if tier == "highValue" else "ST-"
    reward = high_reward if tier == "highValue" else std_reward
    code = prefix + "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
    return {"tier": tier, "reward": reward, "couponCode": code,
            "segment": segment, "guestType": "new" if is_new_guest else "repeat"}


def _seed_customers():
    rng = random.Random(42)
    names = ["Maria G.", "Tom R.", "The Ferris Family", "Dave K.", "Sofia L.", "Ahmed N.",
             "Jenna W.", "Carlos M.", "Priya S.", "The Book Club", "Wes T.", "Grace H.",
             "Leo P.", "Nadia F.", "Sam O."]
    now = datetime.now(timezone.utc)
    custs = []
    for i, name in enumerate(names):
        visits = rng.randint(1, 14)
        avg_ticket = _round(rng.uniform(14, 55))
        sensitivity = _round(rng.choice([0.0, 0.1, 0.2, 0.6, 0.8]))
        days_since = rng.randint(1, 58)
        custs.append({"customerId": f"C{i}", "name": name, "frequency": visits,
                      "avgTicket": avg_ticket, "sensitivity": sensitivity,
                      "daysSinceLast": days_since})
    return custs


CUSTOMERS = _seed_customers()


def rfmd_segment():
    freqs = [c["frequency"] for c in CUSTOMERS]
    tickets = [c["avgTicket"] for c in CUSTOMERS]
    fmin, fmax = min(freqs), max(freqs)
    tmin, tmax = min(tickets), max(tickets)

    def nrm(v, lo, hi):
        return 0 if hi == lo else (v - lo) / (hi - lo)
    rows = []
    for c in CUSTOMERS:
        fn = nrm(c["frequency"], fmin, fmax)
        vn = nrm(c["avgTicket"], tmin, tmax)
        s = c["sensitivity"]
        rn = max(0, (60 - c["daysSinceLast"]) / 60)
        score = _round(0.3 * fn + 0.3 * vn - 0.4 * s + 0.1 * rn)
        if s >= 0.70:
            seg = "promo_pool"
        elif score >= 0.35:
            seg = "vip"
        else:
            seg = "standard"
        row = {**c, "score": score, "segment": seg}
        if seg == "vip":
            row["posNote"] = "VIP Account. Sincere thanks upon checkout. Direct table preference."
        rows.append(row)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def drip_schedule(total_leads=90, days=30):
    daily = -(-total_leads // days)  # ceil
    released = min(daily * 12, total_leads)  # pretend day 12
    return {"totalLeads": total_leads, "days": days, "dailyRate": daily,
            "releasedSoFar": released, "remaining": total_leads - released,
            "revealAtSeconds": 14,
            "steps": [{"day": d + 1, "released": min(daily, max(0, total_leads - daily * d))}
                      for d in range(days)]}


# ===========================================================================
# Pydantic request models
# ===========================================================================
class CopyReq(BaseModel):
    transcript: str


class CriticReq(BaseModel):
    index: int = 0


class SpinReq(BaseModel):
    isNewGuest: bool = True
    segment: str = "new"


# ===========================================================================
# ROUTES
# ===========================================================================
@api.get("/")
async def root():
    return {"service": "omnilocal-1-revenue-engine", "status": "ok"}


@api.get("/overview")
async def overview():
    total_rev = _round(sum(r["totalRevenue"] for r in REPORTS))
    total_spend = _round(sum(r["totalSpend"] for r in REPORTS))
    total_new = sum(r["metrics"]["strategyA"]["newCustomers"] + r["metrics"]["strategyB"]["newCustomers"]
                    for r in REPORTS)
    latest = REPORTS[-1]
    weekly = [{"weekOf": r["weekOf"], "revenue": r["totalRevenue"], "spend": r["totalSpend"],
               "roas": r["blendedRoas"], "shareA": r["allocation"]["strategyA"]["share"],
               "shareB": r["allocation"]["strategyB"]["share"],
               "winner": r["decision"]["winner"]} for r in REPORTS]
    return {
        "brand": BRAND,
        "hero": {
            "totalAttributedRevenue": total_rev,
            "blendedRoas": latest["blendedRoas"],
            "newCustomers": total_new,
            "totalSpend": total_spend,
            "weeksLearning": len(REPORTS),
            "activeCampaigns": 4,
        },
        "weekly": weekly,
        "latestWinner": latest["decision"]["winner"],
        "valpak": {
            "valpakCost": 750, "valpakHomes": 10000, "valpakTargeted": False, "valpakProof": False,
            "ourCost": 299, "ourReachNote": "Targeted to converting ZIPs, tracked to revenue",
            "ourTargeted": True, "ourProof": True,
        },
    }


@api.get("/content/prompts")
async def content_prompts():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return {"prompts": SHOOTING_PROMPTS, "today": daily_prompt(today),
            "assetVault": ASSET_VAULT,
            "distribution": DISTRIBUTION_PATHWAYS,
            "sampleVideos":
            [{"index": i, "filename": v["filename"], "label": v["label"]}
             for i, v in enumerate(SAMPLE_VIDEOS)]}


@api.get("/content/distribution")
async def content_distribution():
    """Distribution pathways the Content Director publishes to via the connector."""
    return {"pathways": DISTRIBUTION_PATHWAYS, "provider": UNIFIED_PROVIDER,
            "connections": {p["id"]: CONNECTIONS[p["id"]] for p in PLATFORMS}}


@api.post("/content/copy")
async def content_copy(req: CopyReq):
    normalized = normalize_transcript(req.transcript)
    return {"normalized": normalized, "drafts": draft_posts(normalized)}


@api.post("/content/critic")
async def content_critic(req: CriticReq):
    idx = max(0, min(req.index, len(SAMPLE_VIDEOS) - 1))
    return {"report": score_video(SAMPLE_VIDEOS[idx]), "label": SAMPLE_VIDEOS[idx]["label"]}


@api.get("/executioner/allocation")
async def executioner_allocation():
    return REPORTS[-1]["allocation"]


@api.get("/executioner/reports")
async def executioner_reports():
    return {"reports": REPORTS, "channelLabels": CHANNEL_LABELS,
            "strategies": {"A": STRATEGY_A, "B": STRATEGY_B}}


@api.post("/executioner/reconcile")
async def executioner_reconcile():
    """Advance the closed loop one more week — 'watch it learn' live."""
    last = REPORTS[-1]
    prev_share_a = last["allocation"]["strategyA"]["share"]
    winner = last["decision"]["winner"]
    if winner == "A":
        share_a = min(0.8, _round(prev_share_a + 0.075))
    elif winner == "B":
        share_a = max(0.2, _round(prev_share_a - 0.075))
    else:
        share_a = prev_share_a
    w = len(REPORTS)
    week_of = _monday(w - (INITIAL_WEEKS - 1))  # seeded weeks end at offset 0; next is +1, +2, ...
    txs, spend_a, spend_b = _seed_week_txs(w, share_a)
    alloc = build_allocation(week_of, share_a)
    ma = _metrics(txs, "STRATA", alloc["strategyA"]["dollars"])
    mb = _metrics(txs, "STRATB", alloc["strategyB"]["dollars"])
    decision = _decide(ma, mb)
    report = {"weekOf": week_of, "allocation": alloc,
              "metrics": {"strategyA": ma, "strategyB": mb},
              "decision": decision, "zipBreakdown": _zip_breakdown(txs),
              "totalRevenue": _round(ma["revenue"] + mb["revenue"]),
              "totalSpend": alloc["totalBudget"],
              "blendedRoas": _round((ma["revenue"] + mb["revenue"]) / alloc["totalBudget"])}
    REPORTS.append(report)
    return {"report": report, "reallocatedTo": decision["winner"]}


@api.post("/executioner/reset")
async def executioner_reset():
    global REPORTS
    REPORTS = build_reports_history(3)
    return {"ok": True, "weeks": len(REPORTS)}


@api.post("/maximizer/spin")
async def maximizer_spin(req: SpinReq):
    return spin(req.isNewGuest, req.segment)


@api.get("/maximizer/segments")
async def maximizer_segments():
    rows = rfmd_segment()
    counts = {"vip": 0, "standard": 0, "promo_pool": 0}
    for r in rows:
        counts[r["segment"]] += 1
    # Verification layer (from POS/CSV): codes redeemed + revenue proof
    verification = {
        "codesIssued": 214, "codesRedeemed": 137, "redemptionRate": 0.64,
        "revenueFromRedemptions": 3184.50,
        "couponers": counts["promo_pool"], "qualityCustomers": counts["vip"],
        "note": "POS/CSV reconciliation separates margin-eroding couponers from high-value regulars.",
    }
    return {"rows": rows, "counts": counts, "verification": verification}


@api.get("/maximizer/drip")
async def maximizer_drip():
    return drip_schedule()


# ===========================================================================
# CONNECTIONS — platform toggles that gate the Ad Engine
# ===========================================================================
PLATFORMS = [
    {"id": "facebook", "label": "Facebook", "default": True},
    {"id": "instagram", "label": "Instagram / Reels", "default": True},
    {"id": "google", "label": "Google Business & Maps", "default": True},
    {"id": "tiktok", "label": "TikTok", "default": False},
    {"id": "youtube", "label": "YouTube", "default": False},
]
CONNECTIONS: Dict[str, bool] = {p["id"]: p["default"] for p in PLATFORMS}

# ---------------------------------------------------------------------------
# DISTRIBUTION PATHWAYS — where Content Director publishes each content type.
# These are the surfaces the Social Media Connector authorizes and posts to.
# ---------------------------------------------------------------------------
DISTRIBUTION_PATHWAYS = [
    {"platform": "google", "label": "Google Business Profile (Maps)", "surface": "GBP Post",
     "contentType": "post", "scope": "business.manage"},
    {"platform": "facebook", "label": "Facebook Reels", "surface": "Reel",
     "contentType": "video", "scope": "pages_manage_posts,pages_read_engagement"},
    {"platform": "instagram", "label": "Instagram Reels", "surface": "Reel",
     "contentType": "video", "scope": "instagram_content_publish"},
    {"platform": "tiktok", "label": "TikTok", "surface": "Short Video",
     "contentType": "video", "scope": "video.publish"},
    {"platform": "youtube", "label": "YouTube Shorts", "surface": "Short",
     "contentType": "video", "scope": "youtube.upload"},
]

# ---------------------------------------------------------------------------
# OAUTH HANDSHAKE — Unified API provider (stubbed until UNIFIED_API_KEY set).
# The connector exposes a start (authorize) + callback (token exchange) flow.
# Tokens are stored in-memory for the demo; real tokens arrive via the provider.
# ---------------------------------------------------------------------------
UNIFIED_PROVIDER = os.environ.get("UNIFIED_SOCIAL_PROVIDER", "unified_api")
UNIFIED_API_KEY = os.environ.get("UNIFIED_API_KEY")  # stubbed until provided
OAUTH_TOKENS: Dict[str, dict] = {}

# Potential paid/organic channels per strategy, each tied to a platform.
CHANNEL_PLATFORM = {
    "facebook_act_now_ads": "facebook", "google_maps_pin_boost": "google",
    "tiktok_spark_ads": "tiktok", "gbp_organic_boost": "google",
    "local_story_drip": "instagram", "youtube_shorts": "youtube",
}
CHANNEL_LABELS.update({"tiktok_spark_ads": "TikTok Spark Ads", "youtube_shorts": "YouTube Shorts"})
STRATEGY_POTENTIAL = {
    "A": {"displayName": "Paid Local Velocity",
          "channels": ["facebook_act_now_ads", "google_maps_pin_boost", "tiktok_spark_ads"]},
    "B": {"displayName": "Organic Community Outreach",
          "channels": ["gbp_organic_boost", "local_story_drip", "youtube_shorts"]},
}


def recommended_plan(total=WEEKLY_BUDGET):
    share_a = REPORTS[-1]["allocation"]["strategyA"]["share"]
    conn = {ch: CONNECTIONS.get(CHANNEL_PLATFORM[ch], False) for ch in CHANNEL_PLATFORM}
    cA = [c for c in STRATEGY_POTENTIAL["A"]["channels"] if conn[c]]
    cB = [c for c in STRATEGY_POTENTIAL["B"]["channels"] if conn[c]]
    exA = [c for c in STRATEGY_POTENTIAL["A"]["channels"] if not conn[c]]
    exB = [c for c in STRATEGY_POTENTIAL["B"]["channels"] if not conn[c]]
    if cA and cB:
        sa = share_a
    elif cA:
        sa = 1.0
    elif cB:
        sa = 0.0
    else:
        sa = 0.0

    def strat(chs, dollars):
        return {"dollars": _round(dollars), "perChannel": _split(chs, dollars) if chs else {}}
    dollars_a = _round(sa * total)
    dollars_b = _round(total - dollars_a)
    connected_count = sum(1 for v in CONNECTIONS.values() if v)
    return {
        "totalBudget": total, "connectedCount": connected_count,
        "strategyA": {"displayName": STRATEGY_POTENTIAL["A"]["displayName"], "share": _round(sa),
                      **strat(cA, dollars_a), "excludedChannels": [{"channel": c, "label": CHANNEL_LABELS[c],
                       "platform": CHANNEL_PLATFORM[c]} for c in exA]},
        "strategyB": {"displayName": STRATEGY_POTENTIAL["B"]["displayName"], "share": _round(1 - sa),
                      **strat(cB, dollars_b), "excludedChannels": [{"channel": c, "label": CHANNEL_LABELS[c],
                       "platform": CHANNEL_PLATFORM[c]} for c in exB]},
        "warning": None if (cA or cB) else "No platforms connected — connect at least one to run campaigns.",
        "diversificationTip": ("Connect 3–4 platforms for the widest reach — people are creatures of habit and "
                               "live on one channel ~80% of the time.") if connected_count < 3 else None,
    }


# ===========================================================================
# CODE SYSTEM — weekly probability-weighted redemption batches + reconciliation
# ===========================================================================
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
REWARD_POOL = [
    {"tier": "grand", "reward": "Free Sub (BOGO)", "weight": 8, "variants": 3},
    {"tier": "high", "reward": "30% Off", "weight": 17, "variants": 4},
    {"tier": "mid", "reward": "20% Off", "weight": 30, "variants": 4},
    {"tier": "low", "reward": "Free Fountain Drink", "weight": 45, "variants": 3},
]


def _gen_code(length, rng):
    return "".join(rng.choice(CODE_ALPHABET) for _ in range(length))


def generate_batch(length=8, week_of=None):
    if length not in (4, 8, 10, 11):
        length = 8
    week_of = week_of or _monday(0)
    rng = random.Random()
    tiers, all_codes = [], {}
    total_weight = sum(t["weight"] for t in REWARD_POOL)
    for t in REWARD_POOL:
        codes = []
        while len(codes) < t["variants"]:
            c = _gen_code(length, rng)
            if c not in all_codes:
                codes.append(c)
                all_codes[c] = {"tier": t["tier"], "reward": t["reward"]}
        tiers.append({"tier": t["tier"], "reward": t["reward"],
                      "probability": _round(t["weight"] / total_weight), "codes": codes})
    expires = (datetime.strptime(week_of, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    return {"weekOf": week_of, "length": length, "issuedAt": week_of, "expiresAt": expires,
            "tiers": tiers, "allCodes": all_codes, "totalCodes": len(all_codes)}


CURRENT_BATCH = generate_batch(8)


def _sample_csv(batch):
    rng = random.Random(7)
    codes = list(batch["allCodes"].keys())
    picked = rng.sample(codes, max(1, int(len(codes) * 0.6)))
    lines = ["promo_code,net_sales"]
    for c in picked:
        lines.append(f"{c},{_round(rng.uniform(12, 44))}")
    # a couple of invalid / never-issued codes
    lines.append(f"{_gen_code(batch['length'], rng)},22.00")
    lines.append(f"{_gen_code(batch['length'], rng)},18.50")
    return "\n".join(lines)


def reconcile_csv(csv_text, batch):
    issued = batch["allCodes"]
    redeemed, invalid, revenue = 0, 0, 0.0
    by_tier = {}
    rows = []
    for i, line in enumerate(csv_text.strip().splitlines()):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        code, amt_s = parts[0], parts[1]
        if i == 0 and not amt_s.replace(".", "").isdigit():
            continue  # header
        try:
            amt = float(amt_s)
        except ValueError:
            continue
        if code in issued:
            redeemed += 1
            revenue = _round(revenue + amt)
            tier = issued[code]["tier"]
            by_tier[tier] = by_tier.get(tier, 0) + 1
            rows.append({"code": code, "net_sales": _round(amt), "reward": issued[code]["reward"], "valid": True})
        else:
            invalid += 1
            rows.append({"code": code, "net_sales": _round(amt), "reward": "—", "valid": False})
    total_issued = len(issued)
    return {"issued": total_issued, "redeemed": redeemed, "invalid": invalid,
            "redemptionRate": _round(redeemed / total_issued) if total_issued else 0,
            "revenue": revenue, "byTier": by_tier, "rows": rows}


class CodeGenReq(BaseModel):
    length: int = 8


class ReconcileReq(BaseModel):
    csv: str


class ConnReq(BaseModel):
    platform: str
    connected: bool


class OAuthCallbackReq(BaseModel):
    platform: str
    code: Optional[str] = None


def _connections_payload():
    return {
        "platforms": [{
            **p,
            "connected": CONNECTIONS[p["id"]],
            "authorized": p["id"] in OAUTH_TOKENS,
            "authMode": OAUTH_TOKENS.get(p["id"], {}).get("mode"),
        } for p in PLATFORMS],
        "connectedCount": sum(1 for v in CONNECTIONS.values() if v),
        "provider": UNIFIED_PROVIDER,
        "liveOAuth": bool(UNIFIED_API_KEY),
    }


@api.get("/connections")
async def get_connections():
    return _connections_payload()


@api.put("/connections")
async def set_connection(req: ConnReq):
    if req.platform in CONNECTIONS:
        CONNECTIONS[req.platform] = req.connected
        if not req.connected:
            OAUTH_TOKENS.pop(req.platform, None)
    return _connections_payload()


@api.get("/connections/pathways")
async def connection_pathways():
    return {"pathways": DISTRIBUTION_PATHWAYS, "provider": UNIFIED_PROVIDER,
            "liveOAuth": bool(UNIFIED_API_KEY)}


@api.get("/connections/oauth/{platform}/start")
async def oauth_start(platform: str):
    """Begin the OAuth handshake — returns the provider authorize URL + state.
    Stubbed until UNIFIED_API_KEY is set; real flow redirects the owner to the
    Unified API provider's hosted authorization screen."""
    if platform not in CONNECTIONS:
        return {"error": "unknown platform"}
    state = "".join(random.choice(CODE_ALPHABET) for _ in range(16))
    authorize_url = (f"https://auth.{UNIFIED_PROVIDER}.example/authorize"
                     f"?platform={platform}&state={state}&provider={UNIFIED_PROVIDER}")
    return {"platform": platform, "state": state, "provider": UNIFIED_PROVIDER,
            "authorizeUrl": authorize_url, "live": bool(UNIFIED_API_KEY),
            "note": "Stubbed handshake. Set UNIFIED_API_KEY to route through the live provider."}


@api.post("/connections/oauth/callback")
async def oauth_callback(req: OAuthCallbackReq):
    """Complete the OAuth handshake — exchanges the code for a token and marks
    the platform authorized/connected. In the stub, a mock token is issued."""
    if req.platform not in CONNECTIONS:
        return {"error": "unknown platform"}
    token = {
        "accessToken": "stub_" + "".join(random.choice(CODE_ALPHABET) for _ in range(24)),
        "provider": UNIFIED_PROVIDER,
        "connectedAt": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if UNIFIED_API_KEY else "stubbed",
    }
    OAUTH_TOKENS[req.platform] = token
    CONNECTIONS[req.platform] = True
    payload = _connections_payload()
    payload["authorized"] = {"platform": req.platform, "mode": token["mode"],
                             "connectedAt": token["connectedAt"]}
    return payload


@api.get("/executioner/recommended-plan")
async def get_recommended_plan():
    return recommended_plan()


@api.get("/codes/current")
async def codes_current():
    b = {k: v for k, v in CURRENT_BATCH.items() if k != "allCodes"}
    return b


@api.post("/codes/generate")
async def codes_generate(req: CodeGenReq):
    global CURRENT_BATCH
    CURRENT_BATCH = generate_batch(req.length)
    return {k: v for k, v in CURRENT_BATCH.items() if k != "allCodes"}


@api.get("/codes/sample-csv")
async def codes_sample_csv():
    return {"csv": _sample_csv(CURRENT_BATCH)}


@api.post("/codes/reconcile")
async def codes_reconcile(req: ReconcileReq):
    return reconcile_csv(req.csv, CURRENT_BATCH)


# ===========================================================================
# QUALITY CUSTOMER MAXIMIZER — 4 rotating games (30-day cycle)
# ===========================================================================
GAMES = [
    {"id": "spin_wheel", "name": "Scan-to-Spin Wheel", "mechanic": "wheel",
     "tagline": "Spin the wheel to reveal your reward.", "month": 1},
    {"id": "scratch_card", "name": "Scratch-to-Win Card", "mechanic": "scratch",
     "tagline": "Scratch the card to uncover your prize.", "month": 2},
    {"id": "mystery_box", "name": "Mystery Prize Vault", "mechanic": "box",
     "tagline": "Choose a vault, unlock a surprise.", "month": 3},
    {"id": "lucky_slots", "name": "Lucky Match Slots", "mechanic": "slots",
     "tagline": "Match three symbols to win big.", "month": 4},
]
ACTIVE_GAME_OVERRIDE: Optional[str] = None


def active_game():
    if ACTIVE_GAME_OVERRIDE:
        g = next((x for x in GAMES if x["id"] == ACTIVE_GAME_OVERRIDE), None)
        if g:
            return {**g, "source": "admin_override"}
    idx = (int(datetime.now(timezone.utc).timestamp()) // (60 * 60 * 24 * 30)) % len(GAMES)
    return {**GAMES[idx], "source": "auto_rotation"}


class GameReq(BaseModel):
    gameId: Optional[str] = None


@api.get("/maximizer/games")
async def maximizer_games():
    return {"games": GAMES, "active": active_game(), "rotationDays": 30, "override": ACTIVE_GAME_OVERRIDE}


@api.put("/maximizer/games/active")
async def maximizer_set_game(req: GameReq):
    global ACTIVE_GAME_OVERRIDE
    ACTIVE_GAME_OVERRIDE = req.gameId or None
    return {"active": active_game(), "override": ACTIVE_GAME_OVERRIDE}


# ===========================================================================
# WEEKLY CUSTOMER CSV IMPORT — segmentation + new-customer welcome trigger
# ===========================================================================
OWNER_VIDEO_URL = os.environ.get(
    "OWNER_WELCOME_VIDEO_URL",
    "https://storage.googleapis.com/omnilocal-assets/owner-welcome-7s.mp4")
WELCOME_SCRIPT = ("Thank you for enrolling and being a part of our rewards program. I'm the owner — "
                  "small businesses are a dying breed, so your support truly matters. Thank you.")
WELCOME_QUEUE: List[dict] = []


class CustomerCsvReq(BaseModel):
    csv: str


def _segment_customer(visits: int, coupon_ratio: float) -> str:
    if visits <= 1:
        return "new"
    if coupon_ratio >= 0.6:
        return "coupon_only"
    return "loyal"


@api.get("/maximizer/sample-customer-csv")
async def sample_customer_csv():
    rng = random.Random(11)
    names = ["Grace H.", "Leo P.", "The Ruiz Family", "Nina B.", "Marcus D.", "Priya S.",
             "Owen T.", "Sasha K.", "Deli Regular", "First Timer Joe", "Coupon Carl", "Loyal Lucy"]
    lines = ["name,email,visits,coupon_ratio"]
    for i, n in enumerate(names):
        v = 1 if i < 3 else rng.randint(2, 12)
        cr = 0.1 if i < 3 else _round(rng.choice([0.0, 0.1, 0.2, 0.7, 0.9]))
        email = n.lower().replace(" ", ".").replace("'", "") + "@example.com"
        lines.append(f"{n},{email},{v},{cr}")
    return {"csv": "\n".join(lines)}


@api.post("/maximizer/import-csv")
async def maximizer_import_csv(req: CustomerCsvReq):
    counts = {"new": 0, "coupon_only": 0, "loyal": 0}
    rows, new_queued = [], 0
    for i, line in enumerate(req.csv.strip().splitlines()):
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        if i == 0 and parts[2].lower() in ("visits", "visit"):
            continue  # header
        name, email = parts[0], parts[1]
        try:
            visits = int(float(parts[2]))
            coupon_ratio = float(parts[3])
        except ValueError:
            continue
        seg = _segment_customer(visits, coupon_ratio)
        counts[seg] += 1
        rows.append({"name": name, "email": email, "visits": visits,
                     "couponRatio": coupon_ratio, "segment": seg})
        if seg == "new":
            new_queued += 1
            scheduled = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
            WELCOME_QUEUE.append({"name": name, "email": email, "status": "queued",
                                  "scheduledAt": scheduled, "channel": "email"})
    return {"imported": len(rows), "segments": counts, "rows": rows,
            "newCustomersQueued": new_queued}


@api.get("/maximizer/welcome-queue")
async def maximizer_welcome_queue():
    return {"queue": WELCOME_QUEUE, "ownerVideoUrl": OWNER_VIDEO_URL, "script": WELCOME_SCRIPT}


# ===========================================================================
# EMAIL ENGINE (Resend) — Anti-Spam Trickle + Welcome Automation
# Sending is STUBBED until RESEND_API_KEY is set. Real sends include mandatory
# Reply-To + List-Unsubscribe headers and a 15s throttle between messages.
# ===========================================================================
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "owner@omnilocal.example")
REPLY_TO_EMAIL = os.environ.get("REPLY_TO_EMAIL", SENDER_EMAIL)
UNSUBSCRIBE_BASE = os.environ.get("UNSUBSCRIBE_BASE_URL", "https://omnilocal.example/unsubscribe")
THROTTLE_SECONDS = 15  # mandatory anti-burst throttle between individual sends


def sanitize_content(text: str) -> dict:
    warnings = []
    words = re.findall(r"[A-Za-z]{4,}", text)
    caps = [w for w in words if w.isupper()]
    if len(caps) >= 3:
        warnings.append(f"{len(caps)} ALL-CAPS words — softens deliverability. Consider sentence case.")
    excl = text.count("!")
    if excl > 2:
        warnings.append(f"{excl} exclamation points — reduce to at most 2 to avoid spam filters.")
    if re.search(r'<img[^>]*(width=["\']?1["\']?|height=["\']?1["\']?)', text, re.IGNORECASE):
        warnings.append("Hidden 1x1 tracking pixel detected — removed for deliverability.")
    cleaned = re.sub(r'<img[^>]*(width=["\']?1["\']?|height=["\']?1["\']?)[^>]*>', "", text, flags=re.IGNORECASE)
    spammy = ["FREE!!!", "ACT NOW", "100% FREE", "CLICK HERE", "LIMITED TIME"]
    hits = [s for s in spammy if s.lower() in text.lower()]
    if hits:
        warnings.append(f"Spam-trigger phrases: {', '.join(hits)}.")
    return {"clean": cleaned, "warnings": warnings, "spamScore": min(len(warnings), 5)}


def build_email_headers(unsub_url: str) -> dict:
    return {
        "Reply-To": REPLY_TO_EMAIL,
        "List-Unsubscribe": f"<{unsub_url}>, <mailto:unsubscribe@{SENDER_EMAIL.split('@')[-1]}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


async def send_via_resend(to: str, subject: str, html: str, unsub_url: str) -> dict:
    headers = build_email_headers(unsub_url)
    if not RESEND_API_KEY:
        logger.info(f"[EMAIL STUB] -> {to} | subj='{subject}' | headers={list(headers)}")
        return {"status": "stubbed", "to": to, "headers": headers,
                "note": "Set RESEND_API_KEY to enable live sending."}
    import resend
    resend.api_key = RESEND_API_KEY
    params = {"from": SENDER_EMAIL, "to": [to], "subject": subject, "html": html, "headers": headers}
    res = await asyncio.to_thread(resend.Emails.send, params)
    return {"status": "sent", "to": to, "id": res.get("id"), "headers": headers}


def trickle_sample_content() -> dict:
    html = ("<h2>A quiet Tuesday story from our kitchen</h2>"
            "<p>Our cook Marco has made the Sunday Gravy every week for nine years. "
            "This week he shared why the sauce simmers for six hours — a family ritual "
            "from his grandmother in Naples.</p>"
            "<p><a href='https://youtube.com/watch?v=demo'>Watch the 90-second story »</a></p>"
            "<p>Because you're part of our community, here's 15% off your next sub — "
            "just show this email at the counter this week.</p>")
    return {"subject": "The six-hour secret behind our Sunday Gravy", "html": html}


class PreviewReq(BaseModel):
    content: str


@api.post("/email/preview")
async def email_preview(req: PreviewReq):
    return sanitize_content(req.content)


@api.get("/email/trickle-plan")
async def email_trickle_plan(total: int = 3000):
    days = 30
    per_day = -(-total // days)
    sample = trickle_sample_content()
    san = sanitize_content(sample["html"])
    return {
        "totalList": total, "days": days, "perDay": per_day,
        "throttleSeconds": THROTTLE_SECONDS,
        "provider": "resend", "liveSending": bool(RESEND_API_KEY),
        "headers": build_email_headers(UNSUBSCRIBE_BASE + "?u=example"),
        "sampleContent": sample, "sanitization": san,
        "philosophy": ("Quality-first: long-form story or video, offer at the end. "
                       f"~{per_day} recipients/day, 1 email every {THROTTLE_SECONDS}s — never a mass blast."),
    }


class SendWelcomeReq(BaseModel):
    index: int = 0


@api.post("/email/send-welcome")
async def email_send_welcome(req: SendWelcomeReq):
    if not WELCOME_QUEUE:
        return {"status": "empty", "note": "No new customers queued. Import a CSV first."}
    idx = max(0, min(req.index, len(WELCOME_QUEUE) - 1))
    item = WELCOME_QUEUE[idx]
    unsub = f"{UNSUBSCRIBE_BASE}?e={item['email']}"
    html = (f"<div style='font-family:sans-serif'><h2>A personal thank-you</h2>"
            f"<p><video src='{OWNER_VIDEO_URL}' controls width='320'></video></p>"
            f"<p>{WELCOME_SCRIPT}</p></div>")
    res = await send_via_resend(item["email"], "A personal thank-you from the owner", html, unsub)
    item["status"] = "sent" if res["status"] in ("sent", "stubbed") else "failed"
    item["deliveryMode"] = res["status"]
    return {"result": res, "videoUrl": OWNER_VIDEO_URL, "queueItem": item}


app.include_router(api)
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"],
)
