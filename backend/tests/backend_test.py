"""Backend API tests for Nosko Handyman."""
import os, io, time, uuid
from datetime import datetime, timezone, timedelta
import pytest, requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://nosko-handyman.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]


def seed_user(role="customer", email=None):
    uid = f"test-user-{uuid.uuid4().hex[:8]}"
    tok = f"test_session_{uuid.uuid4().hex}"
    email = email or f"TEST_{uid}@example.com"
    db.users.insert_one({
        "user_id": uid, "email": email, "name": f"Test {role}",
        "picture": None, "role": role, "referral_code": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    db.user_sessions.insert_one({
        "user_id": uid, "session_token": tok,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return uid, tok, email


@pytest.fixture(scope="session")
def customer():
    uid, tok, email = seed_user("customer")
    yield {"uid": uid, "tok": tok, "email": email, "h": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="session")
def worker():
    uid, tok, email = seed_user("worker")
    yield {"uid": uid, "tok": tok, "email": email, "h": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="session")
def marketer():
    uid, tok, email = seed_user("marketer")
    yield {"uid": uid, "tok": tok, "email": email, "h": {"Authorization": f"Bearer {tok}"}}


@pytest.fixture(scope="session")
def admin():
    uid, tok, email = seed_user("admin")
    yield {"uid": uid, "tok": tok, "email": email, "h": {"Authorization": f"Bearer {tok}"}}


# ---------------- Public endpoints ----------------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("service") == "nosko"


def test_site_settings_defaults():
    r = requests.get(f"{API}/site/settings")
    assert r.status_code == 200
    d = r.json()
    assert "hero_title" in d and "contact_email" in d


def test_portfolio_list_public():
    r = requests.get(f"{API}/portfolio")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_job_no_auth_invalid_referral_nulled():
    payload = {
        "customer_name": "TEST_Cust", "customer_email": "TEST_c@example.com",
        "address": "1 Main", "service_type": "Outlet", "description": "needs fix",
        "referral_code": "BOGUS-9999",
    }
    r = requests.post(f"{API}/jobs", json=payload)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["referral_code"] is None
    assert j["quoted_amount"] == 25.0
    assert j["status"] == "new"
    assert j["job_id"].startswith("job_")


def test_referral_invalid():
    r = requests.get(f"{API}/referral/DOESNOTEXIST123")
    assert r.status_code == 200
    assert r.json() == {"valid": False}


def test_auth_session_bad_id():
    r = requests.post(f"{API}/auth/session", json={"session_id": "invalid_xxx"})
    assert r.status_code == 401


def test_auth_session_missing_id():
    r = requests.post(f"{API}/auth/session", json={})
    assert r.status_code == 400


# ---------------- Auth-gated 401 without auth ----------------
@pytest.mark.parametrize("path", [
    "/auth/me", "/workers/me", "/marketers/me", "/w9/me",
    "/jobs/me", "/payouts/me", "/earnings/summary",
])
def test_auth_required_401(path):
    r = requests.get(f"{API}{path}")
    assert r.status_code == 401


# ---------------- Admin-only 403 for non-admin ----------------
@pytest.mark.parametrize("method,path,body", [
    ("GET", "/jobs", None),
    ("GET", "/workers", None),
    ("GET", "/marketers", None),
    ("GET", "/admin/stats", None),
    ("POST", "/payouts", {"user_id": "x", "amount": 1}),
    ("POST", "/portfolio", {"title": "x", "storage_path": "y"}),
    ("PUT", "/site/settings", {"hero_title": "x"}),
])
def test_admin_only_forbidden(customer, method, path, body):
    r = requests.request(method, f"{API}{path}", json=body, headers=customer["h"])
    assert r.status_code == 403, f"{path}: {r.status_code}"


# ---------------- Auth flows with seeded session ----------------
def test_auth_me_ok(customer):
    r = requests.get(f"{API}/auth/me", headers=customer["h"])
    assert r.status_code == 200
    assert r.json()["email"] == customer["email"]


def test_worker_signup_and_me(worker):
    payload = {"hours_per_week": 20, "skills": ["electrical"], "location": "NYC", "phone": "555", "bio": "test"}
    r = requests.post(f"{API}/workers/signup", json=payload, headers=worker["h"])
    assert r.status_code == 200
    assert r.json()["profile"]["skills"] == ["electrical"]
    r2 = requests.get(f"{API}/workers/me", headers=worker["h"])
    assert r2.status_code == 200
    assert r2.json()["hours_per_week"] == 20


def test_marketer_signup_and_referral(marketer):
    r = requests.post(f"{API}/marketers/signup", json={"phone": "555", "location": "LA"}, headers=marketer["h"])
    assert r.status_code == 200
    code = r.json()["referral_code"]
    assert code and "-" in code
    # Referral check on that code works
    r2 = requests.get(f"{API}/referral/{code}")
    assert r2.status_code == 200
    assert r2.json()["valid"] is True
    # Job with referral attaches the code
    job = {"customer_name": "TEST_R", "customer_email": "TEST_r@x.com", "address": "1", "description": "x", "referral_code": code}
    j = requests.post(f"{API}/jobs", json=job).json()
    assert j["referral_code"] == code


def test_w9_sign(worker):
    payload = {"full_legal_name": "Test W", "ssn_or_ein": "123-45-6789", "address": "1 Main", "typed_signature": "Test W"}
    r = requests.post(f"{API}/w9/sign", json=payload, headers=worker["h"])
    assert r.status_code == 200
    r2 = requests.get(f"{API}/w9/me", headers=worker["h"])
    assert r2.status_code == 200
    assert r2.json()["full_legal_name"] == "Test W"
    assert "ssn_or_ein" not in r2.json()  # masked


# ---------------- Admin flows ----------------
def test_admin_stats(admin):
    r = requests.get(f"{API}/admin/stats", headers=admin["h"])
    assert r.status_code == 200
    for k in ("jobs_total", "workers", "marketers", "payouts_total"):
        assert k in r.json()


def test_admin_list_jobs(admin):
    r = requests.get(f"{API}/jobs", headers=admin["h"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_assign_and_status(admin, worker):
    j = requests.post(f"{API}/jobs", json={
        "customer_name": "TEST_A", "customer_email": "TEST_a@x.com", "address": "1", "description": "x"
    }).json()
    jid = j["job_id"]
    r = requests.put(f"{API}/jobs/{jid}/assign", json={"worker_id": worker["uid"]}, headers=admin["h"])
    assert r.status_code == 200
    r2 = requests.put(f"{API}/jobs/{jid}/status", json={"status": "completed"}, headers=admin["h"])
    assert r2.status_code == 200
    # Verify via /jobs/me for worker
    mine = requests.get(f"{API}/jobs/me", headers=worker["h"]).json()
    assert any(x["job_id"] == jid and x["status"] == "completed" for x in mine)
    # Bad status
    r3 = requests.put(f"{API}/jobs/{jid}/status", json={"status": "bogus"}, headers=admin["h"])
    assert r3.status_code == 400
    # Not found
    r4 = requests.put(f"{API}/jobs/nope/assign", json={"worker_id": worker["uid"]}, headers=admin["h"])
    assert r4.status_code == 404


def test_payout_and_earnings(admin, worker):
    r = requests.post(f"{API}/payouts", json={"user_id": worker["uid"], "amount": 50, "type": "work"}, headers=admin["h"])
    assert r.status_code == 200
    assert r.json()["status"] == "paid"
    # Worker earnings summary aggregates
    s = requests.get(f"{API}/earnings/summary", headers=worker["h"]).json()
    assert s["weekly"] >= 50
    assert s["all_time"] >= 50
    assert len(s["series"]) == 12
    # Worker sees own payouts
    pm = requests.get(f"{API}/payouts/me", headers=worker["h"]).json()
    assert any(p["amount"] == 50 for p in pm)


def test_site_settings_update(admin):
    new_title = f"TEST_TITLE_{uuid.uuid4().hex[:6]}"
    r = requests.put(f"{API}/site/settings", json={"hero_title": new_title, "ignored_field": "x"}, headers=admin["h"])
    assert r.status_code == 200
    assert r.json()["hero_title"] == new_title
    r2 = requests.get(f"{API}/site/settings")
    assert r2.json()["hero_title"] == new_title


def test_portfolio_crud(admin):
    r = requests.post(f"{API}/portfolio", json={"title": "TEST_P", "storage_path": "nosko/portfolio/x.jpg", "description": "d"}, headers=admin["h"])
    assert r.status_code == 200
    pid = r.json()["photo_id"]
    items = requests.get(f"{API}/portfolio").json()
    assert any(i["photo_id"] == pid for i in items)
    rd = requests.delete(f"{API}/portfolio/{pid}", headers=admin["h"])
    assert rd.status_code == 200
    rd2 = requests.delete(f"{API}/portfolio/{pid}", headers=admin["h"])
    assert rd2.status_code == 404


def test_upload_and_serve():
    files = {"file": ("test.txt", io.BytesIO(b"hello-nosko"), "text/plain")}
    r = requests.post(f"{API}/upload", files=files, data={"folder": "tests"})
    if r.status_code == 503:
        pytest.skip("Object storage unavailable")
    assert r.status_code == 200, r.text
    path = r.json()["path"]
    assert path
    rg = requests.get(f"{API}/files/{path}")
    assert rg.status_code == 200
    assert b"hello-nosko" in rg.content


# ---------------- Cleanup ----------------
def teardown_module(module):
    db.users.delete_many({"email": {"$regex": "^TEST_"}})
    db.users.delete_many({"user_id": {"$regex": "^test-user-"}})
    db.user_sessions.delete_many({"session_token": {"$regex": "^test_session_"}})
    db.jobs.delete_many({"customer_email": {"$regex": "^TEST_"}})
    db.portfolio.delete_many({"title": {"$regex": "^TEST_"}})
    db.site_settings.delete_many({"hero_title": {"$regex": "^TEST_TITLE_"}})
