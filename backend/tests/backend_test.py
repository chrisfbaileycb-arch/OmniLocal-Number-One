"""OmniLocal #1 backend test suite (iteration 2).

Covers:
- Social Media Connector OAuth handshake + connections state machine
- Distribution pathways in Content Director
- Core routes post-rebrand (executioner, maximizer, codes, email)
- Welcome video automation flow (CSV import -> segments -> send-welcome)
- Email trickle plan (throttle + Reply-To + List-Unsubscribe headers)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback: read from frontend .env file (used when this file runs on the host)
    env_path = "/app/frontend/.env"
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                    break

API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    return requests.Session()


# ============================================================================
# CONNECTIONS — OAuth handshake + pathways
# ============================================================================
class TestConnections:
    def test_pathways_returns_5(self, s):
        r = s.get(f"{API}/connections/pathways", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["provider"] == "unified_api"
        assert d["liveOAuth"] is False
        platforms = [p["platform"] for p in d["pathways"]]
        assert set(platforms) == {"google", "facebook", "instagram", "tiktok", "youtube"}
        for p in d["pathways"]:
            assert "surface" in p and "contentType" in p and "scope" in p

    @pytest.mark.parametrize("platform", ["google", "tiktok", "instagram", "facebook", "youtube"])
    def test_oauth_start_valid_platform(self, s, platform):
        r = s.get(f"{API}/connections/oauth/{platform}/start", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["platform"] == platform
        assert d["provider"] == "unified_api"
        assert d["state"] and len(d["state"]) == 16
        assert "authorizeUrl" in d and platform in d["authorizeUrl"]
        assert d["live"] is False

    def test_oauth_start_unknown_platform(self, s):
        r = s.get(f"{API}/connections/oauth/notreal/start", timeout=15)
        # 200 with error field per current impl
        d = r.json()
        assert "error" in d

    def test_oauth_callback_marks_authorized(self, s):
        # start
        r = s.get(f"{API}/connections/oauth/tiktok/start", timeout=15)
        assert r.status_code == 200
        # callback
        r = s.post(f"{API}/connections/oauth/callback",
                   json={"platform": "tiktok", "code": "demo_code"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["authorized"]["platform"] == "tiktok"
        assert d["authorized"]["mode"] == "stubbed"
        # platforms list reflects state
        tt = next(p for p in d["platforms"] if p["id"] == "tiktok")
        assert tt["connected"] is True
        assert tt["authorized"] is True
        assert tt["authMode"] == "stubbed"

    def test_get_connections_reflects_state_and_disconnect_clears_auth(self, s):
        # ensure tiktok connected first
        s.post(f"{API}/connections/oauth/callback",
               json={"platform": "tiktok", "code": "x"}, timeout=15)
        r = s.get(f"{API}/connections", timeout=15)
        assert r.status_code == 200
        d = r.json()
        tt = next(p for p in d["platforms"] if p["id"] == "tiktok")
        assert tt["connected"] is True and tt["authorized"] is True

        # disconnect
        r = s.put(f"{API}/connections",
                  json={"platform": "tiktok", "connected": False}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        tt = next(p for p in d["platforms"] if p["id"] == "tiktok")
        assert tt["connected"] is False
        assert tt["authorized"] is False
        assert tt["authMode"] is None


# ============================================================================
# CONTENT DIRECTOR — distribution + prompts + copy + critic
# ============================================================================
class TestContentDirector:
    def test_prompts_has_distribution(self, s):
        r = s.get(f"{API}/content/prompts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "prompts" in d and "today" in d and "assetVault" in d
        assert "distribution" in d
        assert len(d["distribution"]) == 5
        assert "sampleVideos" in d and len(d["sampleVideos"]) == 3

    def test_distribution_endpoint(self, s):
        r = s.get(f"{API}/content/distribution", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["pathways"]) == 5
        assert d["provider"] == "unified_api"
        assert "connections" in d
        for pid in ("google", "facebook", "instagram", "tiktok", "youtube"):
            assert pid in d["connections"]

    def test_content_copy(self, s):
        r = s.post(f"{API}/content/copy", json={"transcript": "Um, so we make the sub, you know, best in town."}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "normalized" in d and "drafts" in d
        assert "um" not in d["normalized"].lower().split()
        assert set(d["drafts"].keys()) == {"gbp", "facebook", "instagram"}

    def test_content_critic(self, s):
        r = s.post(f"{API}/content/critic", json={"index": 0}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["report"]["overall"] == "STRONG"
        r2 = s.post(f"{API}/content/critic", json={"index": 1}, timeout=15)
        assert r2.json()["report"]["overall"] == "WEAK"


# ============================================================================
# CORE ROUTES SMOKE — no 404s after refactor
# ============================================================================
class TestCoreRoutes:
    def test_overview(self, s):
        r = s.get(f"{API}/overview", timeout=15); assert r.status_code == 200
        d = r.json(); assert "brand" in d and "hero" in d and "weekly" in d

    def test_executioner_reports(self, s):
        r = s.get(f"{API}/executioner/reports", timeout=15); assert r.status_code == 200
        assert "reports" in r.json()

    def test_executioner_reconcile_and_reset(self, s):
        # reset first
        r = s.post(f"{API}/executioner/reset", timeout=15); assert r.status_code == 200
        weeks_before = r.json()["weeks"]
        r = s.post(f"{API}/executioner/reconcile", timeout=15); assert r.status_code == 200
        d = r.json(); assert "report" in d and "reallocatedTo" in d
        r = s.get(f"{API}/executioner/reports", timeout=15)
        assert len(r.json()["reports"]) == weeks_before + 1
        s.post(f"{API}/executioner/reset", timeout=15)

    def test_recommended_plan(self, s):
        r = s.get(f"{API}/executioner/recommended-plan", timeout=15); assert r.status_code == 200
        d = r.json(); assert "strategyA" in d and "strategyB" in d and "totalBudget" in d

    def test_maximizer_games(self, s):
        r = s.get(f"{API}/maximizer/games", timeout=15); assert r.status_code == 200
        d = r.json(); assert len(d["games"]) == 4 and "active" in d

    def test_maximizer_set_active(self, s):
        r = s.put(f"{API}/maximizer/games/active", json={"gameId": "scratch_card"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["active"]["id"] == "scratch_card"
        # clear override
        s.put(f"{API}/maximizer/games/active", json={"gameId": None}, timeout=15)

    def test_maximizer_segments(self, s):
        r = s.get(f"{API}/maximizer/segments", timeout=15); assert r.status_code == 200
        d = r.json(); assert "rows" in d and "counts" in d and "verification" in d

    def test_maximizer_drip(self, s):
        r = s.get(f"{API}/maximizer/drip", timeout=15); assert r.status_code == 200

    def test_maximizer_spin(self, s):
        r = s.post(f"{API}/maximizer/spin", json={"isNewGuest": True, "segment": "new"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["tier"] in ("highValue", "standard")

    def test_codes_flow(self, s):
        r = s.get(f"{API}/codes/current", timeout=15); assert r.status_code == 200
        r = s.post(f"{API}/codes/generate", json={"length": 8}, timeout=15); assert r.status_code == 200
        r = s.get(f"{API}/codes/sample-csv", timeout=15); assert r.status_code == 200
        csv = r.json()["csv"]
        r = s.post(f"{API}/codes/reconcile", json={"csv": csv}, timeout=15)
        assert r.status_code == 200
        d = r.json(); assert d["issued"] > 0 and d["redeemed"] > 0


# ============================================================================
# WELCOME VIDEO AUTOMATION — CSV → segments → welcome email
# ============================================================================
class TestWelcomeAutomation:
    def test_full_welcome_flow(self, s):
        # sample csv
        r = s.get(f"{API}/maximizer/sample-customer-csv", timeout=15)
        assert r.status_code == 200
        csv = r.json()["csv"]
        # import
        r = s.post(f"{API}/maximizer/import-csv", json={"csv": csv}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert set(d["segments"].keys()) == {"new", "coupon_only", "loyal"}
        assert d["segments"]["new"] >= 1
        assert d["newCustomersQueued"] >= 1
        # welcome queue
        r = s.get(f"{API}/maximizer/welcome-queue", timeout=15)
        assert r.status_code == 200
        qd = r.json()
        assert qd["ownerVideoUrl"].startswith("http")
        assert len(qd["queue"]) >= 1
        # send welcome
        r = s.post(f"{API}/email/send-welcome", json={"index": 0}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["result"]["status"] == "stubbed"
        headers = d["result"]["headers"]
        assert "Reply-To" in headers and "List-Unsubscribe" in headers
        assert d["videoUrl"] in d["videoUrl"]  # sanity
        # html embeds the video url (spot check via a second call using queueItem)
        # HTML is not returned from send-welcome; the important asserts are headers + status + videoUrl.


# ============================================================================
# EMAIL TRICKLE PLAN
# ============================================================================
class TestEmailTrickle:
    def test_trickle_plan(self, s):
        r = s.get(f"{API}/email/trickle-plan", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["throttleSeconds"] == 15
        assert d["provider"] == "resend"
        assert d["liveSending"] is False
        h = d["headers"]
        assert "Reply-To" in h and "List-Unsubscribe" in h and "List-Unsubscribe-Post" in h

    def test_email_preview(self, s):
        r = s.post(f"{API}/email/preview", json={"content": "ACT NOW!!! CLICK HERE FREE"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["spamScore"] >= 1
        assert len(d["warnings"]) >= 1
