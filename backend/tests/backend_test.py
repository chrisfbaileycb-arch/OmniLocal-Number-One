"""Expo Proxy backend API tests — validates all engines end-to-end."""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
    "https://emergent-ai-builder-11.preview.emergentagent.com"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------
class TestHealth:
    def test_root(self, client):
        r = client.get(f"{API}/")
        assert r.status_code == 200
        d = r.json()
        assert d.get("status") == "ok"


# ---------------------------------------------------------------------------
# Overview (Command Center)
# ---------------------------------------------------------------------------
class TestOverview:
    def test_overview_shape(self, client):
        r = client.get(f"{API}/overview")
        assert r.status_code == 200
        d = r.json()
        assert set(["brand", "hero", "weekly", "latestWinner", "valpak"]).issubset(d.keys())
        hero = d["hero"]
        for k in ["totalAttributedRevenue", "blendedRoas", "newCustomers",
                  "totalSpend", "weeksLearning", "activeCampaigns"]:
            assert k in hero, f"missing hero.{k}"
        assert hero["totalAttributedRevenue"] > 0
        assert hero["blendedRoas"] > 0
        assert hero["newCustomers"] > 0
        assert len(d["weekly"]) == 5
        for w in d["weekly"]:
            for k in ["weekOf", "revenue", "spend", "roas", "shareA", "shareB", "winner"]:
                assert k in w
        assert d["latestWinner"] in ("A", "B", "tie")
        assert d["valpak"]["ourCost"] == 299
        assert d["valpak"]["valpakCost"] == 750


# ---------------------------------------------------------------------------
# Content Director — prompts, copy, critic
# ---------------------------------------------------------------------------
class TestContent:
    def test_prompts(self, client):
        r = client.get(f"{API}/content/prompts")
        assert r.status_code == 200
        d = r.json()
        assert "today" in d and "title" in d["today"]
        assert len(d["prompts"]) >= 5
        assert len(d["assetVault"]) >= 3
        assert len(d["sampleVideos"]) == 3
        assert d["sampleVideos"][0]["index"] == 0

    def test_copy_removes_fillers(self, client):
        transcript = "Um, so today we're, we're making the the Sunday Gravy Sub, you know, and, uh, the secret."
        r = client.post(f"{API}/content/copy", json={"transcript": transcript})
        assert r.status_code == 200
        d = r.json()
        norm = d["normalized"].lower()
        for filler in [" um ", " uh ", "you know", " we're we're", " the the"]:
            assert filler not in norm, f"filler still present: {filler!r} -> {norm}"
        # Duplicates collapsed
        assert "we're we're" not in norm
        assert "the the" not in norm
        # Drafts shape
        drafts = d["drafts"]
        assert set(drafts.keys()) == {"gbp", "facebook", "instagram"}
        assert len(drafts["gbp"]) > 20
        assert "#" in drafts["instagram"]

    def test_copy_empty_transcript(self, client):
        r = client.post(f"{API}/content/copy", json={"transcript": ""})
        assert r.status_code == 200
        d = r.json()
        assert d["normalized"] == ""

    def test_critic_index0_strong(self, client):
        r = client.post(f"{API}/content/critic", json={"index": 0})
        assert r.status_code == 200
        d = r.json()
        rep = d["report"]
        # dinner-rush: action opener, high energy, front lit → STRONG overall
        assert rep["overall"] == "STRONG", f"expected STRONG got {rep['overall']}"
        assert rep["hook"]["grade"] == "STRONG"
        assert rep["audio"]["grade"] == "STRONG"
        assert rep["framing"]["grade"] == "STRONG"

    def test_critic_index1_weak(self, client):
        r = client.post(f"{API}/content/critic", json={"index": 1})
        assert r.status_code == 200
        rep = r.json()["report"]
        # owner-intro: no action opener, back-lit, flat audio → WEAK overall
        assert rep["overall"] == "WEAK", f"expected WEAK got {rep['overall']}"
        assert rep["hook"]["grade"] == "WEAK"

    def test_critic_index2(self, client):
        r = client.post(f"{API}/content/critic", json={"index": 2})
        assert r.status_code == 200
        rep = r.json()["report"]
        # menu-tour: side lit + cut off + clutter → framing WEAK dominates
        assert rep["overall"] in ("WEAK", "MODERATE", "IMPROVABLE")

    def test_critic_out_of_range_clamped(self, client):
        r = client.post(f"{API}/content/critic", json={"index": 99})
        assert r.status_code == 200
        # Should clamp to index 2 (menu-tour)
        assert "menu-tour" in r.json()["report"]["filename"]


# ---------------------------------------------------------------------------
# AdSmith — closed loop
# ---------------------------------------------------------------------------
class TestAdSmith:
    def test_reports_shape(self, client):
        # Ensure known state
        client.post(f"{API}/adsmith/reset")
        r = client.get(f"{API}/adsmith/reports")
        assert r.status_code == 200
        d = r.json()
        assert len(d["reports"]) == 5
        assert "A" in d["strategies"] and "B" in d["strategies"]
        first_share = d["reports"][0]["allocation"]["strategyA"]["share"]
        assert abs(first_share - 0.5) < 1e-6, "week 1 must start 50/50"
        # Strategy A should generally win by end (paid velocity seeded higher ROAS)
        last = d["reports"][-1]
        for k in ["allocation", "metrics", "decision", "zipBreakdown",
                  "totalRevenue", "totalSpend", "blendedRoas"]:
            assert k in last

    def test_reconcile_shifts_toward_winner(self, client):
        client.post(f"{API}/adsmith/reset")
        before = client.get(f"{API}/adsmith/reports").json()
        prev = before["reports"][-1]
        prev_share_a = prev["allocation"]["strategyA"]["share"]
        winner = prev["decision"]["winner"]

        r = client.post(f"{API}/adsmith/reconcile")
        assert r.status_code == 200
        rep = r.json()["report"]
        new_share_a = rep["allocation"]["strategyA"]["share"]

        if winner == "A":
            assert new_share_a > prev_share_a or new_share_a >= 0.8
        elif winner == "B":
            assert new_share_a < prev_share_a or new_share_a <= 0.2
        # Bounded
        assert 0.2 <= new_share_a <= 0.8

        after = client.get(f"{API}/adsmith/reports").json()
        assert len(after["reports"]) == 6

    def test_reset_restores_five_weeks(self, client):
        # Add a couple weeks
        client.post(f"{API}/adsmith/reconcile")
        client.post(f"{API}/adsmith/reconcile")
        r = client.post(f"{API}/adsmith/reset")
        assert r.status_code == 200
        assert r.json()["weeks"] == 5
        d = client.get(f"{API}/adsmith/reports").json()
        assert len(d["reports"]) == 5


# ---------------------------------------------------------------------------
# EchoLink — spin, segments, drip
# ---------------------------------------------------------------------------
class TestEchoLink:
    def test_spin_new_guest_skews_highvalue(self, client):
        results = []
        for _ in range(60):
            r = client.post(f"{API}/echolink/spin", json={"isNewGuest": True})
            assert r.status_code == 200
            results.append(r.json())
        for res in results:
            assert set(["tier", "reward", "couponCode", "segment", "guestType"]).issubset(res.keys())
            assert res["tier"] in ("highValue", "standard")
            assert res["guestType"] == "new"
        hv = sum(1 for r in results if r["tier"] == "highValue")
        # theoretical 80% — accept >=55% for 60 samples (variance safe)
        assert hv / len(results) > 0.55, f"new guests: only {hv}/{len(results)} highValue"

    def test_spin_repeat_skews_standard(self, client):
        results = []
        for _ in range(60):
            r = client.post(f"{API}/echolink/spin", json={"isNewGuest": False})
            assert r.status_code == 200
            results.append(r.json())
        std = sum(1 for r in results if r["tier"] == "standard")
        # theoretical 90% standard — accept >=70%
        assert std / len(results) > 0.70, f"repeat guests: only {std}/{len(results)} standard"

    def test_segments(self, client):
        r = client.get(f"{API}/echolink/segments")
        assert r.status_code == 200
        d = r.json()
        assert "rows" in d and "counts" in d
        assert set(d["counts"].keys()) == {"vip", "standard", "promo_pool"}
        assert len(d["rows"]) == sum(d["counts"].values())
        assert d["counts"]["vip"] > 0, "expect at least one VIP"
        assert d["counts"]["promo_pool"] > 0, "expect at least one promo pool"
        for row in d["rows"]:
            for k in ["customerId", "name", "frequency", "avgTicket", "score", "segment"]:
                assert k in row
        assert "verification" in d

    def test_drip(self, client):
        r = client.get(f"{API}/echolink/drip")
        assert r.status_code == 200
        d = r.json()
        assert d["days"] == 30
        assert len(d["steps"]) == 30
        assert d["releasedSoFar"] > 0
        assert d["revealAtSeconds"] == 14
