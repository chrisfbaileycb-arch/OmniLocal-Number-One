"""
Expo Proxy — Unified Restaurant Revenue Engine (demo backend).

Faithfully ports the deterministic engines from the three source repos:
  - Content Director : shooting prompts, transcript->copy, Brutal Honesty Critic
  - AdSmith          : closed-loop weekly budget allocation + A/B learning
  - EchoLink         : Scan-to-Spin odds, RFMD VIP segmenting, slow-trickle drip

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
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI(title="Expo Proxy Revenue Engine")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("expo-proxy")

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
# ADSMITH — strategies + closed-loop budget engine
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
# ECHOLINK — odds, RFMD, drip
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
    return {"service": "expo-proxy-revenue-engine", "status": "ok"}


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
            "assetVault": ASSET_VAULT, "sampleVideos":
            [{"index": i, "filename": v["filename"], "label": v["label"]}
             for i, v in enumerate(SAMPLE_VIDEOS)]}


@api.post("/content/copy")
async def content_copy(req: CopyReq):
    normalized = normalize_transcript(req.transcript)
    return {"normalized": normalized, "drafts": draft_posts(normalized)}


@api.post("/content/critic")
async def content_critic(req: CriticReq):
    idx = max(0, min(req.index, len(SAMPLE_VIDEOS) - 1))
    return {"report": score_video(SAMPLE_VIDEOS[idx]), "label": SAMPLE_VIDEOS[idx]["label"]}


@api.get("/adsmith/allocation")
async def adsmith_allocation():
    return REPORTS[-1]["allocation"]


@api.get("/adsmith/reports")
async def adsmith_reports():
    return {"reports": REPORTS, "channelLabels": CHANNEL_LABELS,
            "strategies": {"A": STRATEGY_A, "B": STRATEGY_B}}


@api.post("/adsmith/reconcile")
async def adsmith_reconcile():
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


@api.post("/adsmith/reset")
async def adsmith_reset():
    global REPORTS
    REPORTS = build_reports_history(3)
    return {"ok": True, "weeks": len(REPORTS)}


@api.post("/echolink/spin")
async def echolink_spin(req: SpinReq):
    return spin(req.isNewGuest, req.segment)


@api.get("/echolink/segments")
async def echolink_segments():
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


@api.get("/echolink/drip")
async def echolink_drip():
    return drip_schedule()


# ===========================================================================
# CONNECTIONS — platform toggles that gate AdSmith
# ===========================================================================
PLATFORMS = [
    {"id": "facebook", "label": "Facebook", "default": True},
    {"id": "instagram", "label": "Instagram / Reels", "default": True},
    {"id": "google", "label": "Google Business & Maps", "default": True},
    {"id": "tiktok", "label": "TikTok", "default": False},
    {"id": "youtube", "label": "YouTube", "default": False},
]
CONNECTIONS: Dict[str, bool] = {p["id"]: p["default"] for p in PLATFORMS}

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


@api.get("/connections")
async def get_connections():
    return {"platforms": [{**p, "connected": CONNECTIONS[p["id"]]} for p in PLATFORMS],
            "connectedCount": sum(1 for v in CONNECTIONS.values() if v)}


@api.put("/connections")
async def set_connection(req: ConnReq):
    if req.platform in CONNECTIONS:
        CONNECTIONS[req.platform] = req.connected
    return {"platforms": [{**p, "connected": CONNECTIONS[p["id"]]} for p in PLATFORMS],
            "connectedCount": sum(1 for v in CONNECTIONS.values() if v)}


@api.get("/adsmith/recommended-plan")
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


app.include_router(api)
app.add_middleware(
    CORSMiddleware, allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"], allow_headers=["*"],
)
