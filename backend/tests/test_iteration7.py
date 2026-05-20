"""Iteration 7 backend tests:
- GET/PUT /api/availability (auth/role gating, validation, idempotent replace)
- POST /api/jobs rejects blocked preferred_date
- POST /api/upload (folder=portfolio) accepts image and returns nosko/portfolio/...
- POST /api/portfolio with uploaded path + GET /api/portfolio includes storage_path
- GET /api/files/{path} returns raw image bytes
- PUT /api/site/settings preserves services[].image_path on round-trip
"""
import io
import os
import uuid
import struct
import zlib

import pytest
import requests
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://nosko-handyman.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

mc = MongoClient(MONGO_URL)
db = mc[DB_NAME]

FOUNDER_EMAIL = "noskotx@gmail.com"
FOUNDER_PASSWORD = "AdminTest12345"


# ---------------- Helpers ----------------

def _cleanup_email(email: str):
    user = db.users.find_one({"email": email}, {"_id": 0, "user_id": 1})
    if user:
        db.user_sessions.delete_many({"user_id": user["user_id"]})
        db.password_reset_tokens.delete_many({"user_id": user["user_id"]})
    db.users.delete_many({"email": email})


def _ensure_founder_admin():
    r = requests.post(f"{API}/auth/register",
                      json={"email": FOUNDER_EMAIL, "password": FOUNDER_PASSWORD, "name": "Nosko Admin"})
    if r.status_code == 200:
        token = r.json()["session_token"]
    elif r.status_code == 409:
        lr = requests.post(f"{API}/auth/login",
                           json={"email": FOUNDER_EMAIL, "password": FOUNDER_PASSWORD})
        assert lr.status_code == 200, lr.text
        token = lr.json()["session_token"]
    else:
        pytest.skip(f"Founder register/login failed: {r.status_code} {r.text}")
    me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["role"] == "admin", me.text
    return token


def _register_customer():
    email = f"TEST_iter7_{uuid.uuid4().hex[:8]}@example.com"
    _cleanup_email(email)
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "Password1234", "name": "Cust"})
    assert r.status_code == 200, r.text
    return email, r.json()["session_token"]


def _png_bytes(width: int = 4, height: int = 4) -> bytes:
    """Build a minimal valid PNG (red 4x4) without requiring Pillow."""
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b""
    for _ in range(height):
        raw += b"\x00" + (b"\xff\x00\x00" * width)
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="module")
def admin_token():
    return _ensure_founder_admin()


@pytest.fixture(scope="module")
def customer_token():
    _, tok = _register_customer()
    return tok


@pytest.fixture(scope="module", autouse=True)
def reset_availability_at_end():
    # Run tests
    yield
    # Cleanup — reset availability to empty so other suites are not affected
    try:
        tok = _ensure_founder_admin()
        requests.put(f"{API}/availability",
                     json={"blocked_dates": []},
                     headers={"Authorization": f"Bearer {tok}"})
    except Exception:
        pass


# ---------------- Availability tests ----------------

class TestAvailability:
    def test_get_availability_public_no_auth(self):
        # Reset first
        db.availability.update_one({"key": "default"},
                                    {"$set": {"key": "default", "blocked_dates": []}},
                                    upsert=True)
        r = requests.get(f"{API}/availability")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "blocked_dates" in data
        assert isinstance(data["blocked_dates"], list)
        assert data["blocked_dates"] == []

    def test_put_availability_without_auth_401(self):
        r = requests.put(f"{API}/availability",
                         json={"blocked_dates": ["2026-03-15"]})
        assert r.status_code == 401, r.text

    def test_put_availability_non_admin_403(self, customer_token):
        r = requests.put(f"{API}/availability",
                         json={"blocked_dates": ["2026-03-15"]},
                         headers={"Authorization": f"Bearer {customer_token}"})
        assert r.status_code == 403, r.text

    def test_put_availability_admin_sets_dates_sorted_and_deduped(self, admin_token):
        r = requests.put(f"{API}/availability",
                         json={"blocked_dates": ["2026-03-16", "2026-03-15", "2026-03-15"]},
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["blocked_dates"] == ["2026-03-15", "2026-03-16"]

        # GET should reflect persisted state
        g = requests.get(f"{API}/availability")
        assert g.status_code == 200
        assert g.json()["blocked_dates"] == ["2026-03-15", "2026-03-16"]

    def test_put_availability_invalid_format_400(self, admin_token):
        r = requests.put(f"{API}/availability",
                         json={"blocked_dates": "2026-03-15"},
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 400, r.text

    def test_put_availability_replaces_full_set(self, admin_token):
        # Now overwrite with a different set; old dates should be gone
        r = requests.put(f"{API}/availability",
                         json={"blocked_dates": ["2026-04-01"]},
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200
        assert r.json()["blocked_dates"] == ["2026-04-01"]
        g = requests.get(f"{API}/availability").json()
        assert g["blocked_dates"] == ["2026-04-01"]


# ---------------- Jobs vs blocked dates ----------------

class TestJobBlockedDate:
    def test_create_job_blocked_date_rejected_400(self, admin_token):
        # Block 2026-03-15
        requests.put(f"{API}/availability",
                     json={"blocked_dates": ["2026-03-15"]},
                     headers={"Authorization": f"Bearer {admin_token}"})
        payload = {
            "customer_name": "TEST_Blocked",
            "customer_email": "TEST_blocked@example.com",
            "address": "1 Test Ln",
            "service_type": "General Handyman",
            "description": "blocked-date test",
            "preferred_date": "2026-03-15",
            "preferred_time_slot": "morning",
            "quoted_amount": 100,
        }
        r = requests.post(f"{API}/jobs", json=payload)
        assert r.status_code == 400, r.text
        body = r.text.lower()
        assert "unavailable" in body or "blocked" in body or "another day" in body

    def test_create_job_unblocked_date_succeeds(self, admin_token):
        # 2026-03-20 not in blocked list (only 2026-03-15)
        payload = {
            "customer_name": "TEST_OkDate",
            "customer_email": "TEST_okdate@example.com",
            "address": "2 Test Ln",
            "service_type": "General Handyman",
            "description": "good-date test",
            "preferred_date": "2026-03-20",
            "preferred_time_slot": "afternoon",
            "quoted_amount": 120,
        }
        r = requests.post(f"{API}/jobs", json=payload)
        assert r.status_code == 200, r.text
        job = r.json()
        assert job["preferred_date"] == "2026-03-20"
        assert job["preferred_time_slot"] == "afternoon"
        # cleanup
        db.jobs.delete_many({"job_id": job["job_id"]})


# ---------------- Upload + Portfolio + Files ----------------

class TestUploadPortfolioFiles:
    """End-to-end: upload an image, create portfolio item, fetch image bytes back."""

    def test_upload_portfolio_image_returns_path(self):
        png = _png_bytes()
        files = {"file": ("tiny.png", io.BytesIO(png), "image/png")}
        data = {"folder": "portfolio"}
        r = requests.post(f"{API}/upload", files=files, data=data)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "path" in body
        assert body["path"].startswith("nosko/portfolio/")
        assert body["path"].endswith(".png")
        # Stash on class for next test
        TestUploadPortfolioFiles._uploaded_path = body["path"]

    def test_create_portfolio_item_admin(self, admin_token):
        path = getattr(TestUploadPortfolioFiles, "_uploaded_path", None)
        assert path, "Previous upload test must have run"
        r = requests.post(f"{API}/portfolio",
                          json={"title": "TEST_iter7 portfolio",
                                "description": "iter7 test",
                                "storage_path": path},
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, r.text
        item = r.json()
        assert item["title"] == "TEST_iter7 portfolio"
        assert item["storage_path"] == path
        assert "photo_id" in item
        TestUploadPortfolioFiles._photo_id = item["photo_id"]

    def test_get_portfolio_includes_uploaded_item(self):
        r = requests.get(f"{API}/portfolio")
        assert r.status_code == 200
        items = r.json()
        photo_id = getattr(TestUploadPortfolioFiles, "_photo_id", None)
        path = getattr(TestUploadPortfolioFiles, "_uploaded_path", None)
        found = next((it for it in items if it.get("photo_id") == photo_id), None)
        assert found is not None, "Created portfolio item not in GET list"
        assert found["storage_path"] == path
        assert found["title"] == "TEST_iter7 portfolio"

    def test_get_files_returns_bytes(self):
        path = getattr(TestUploadPortfolioFiles, "_uploaded_path", None)
        r = requests.get(f"{API}/files/{path}")
        assert r.status_code == 200, r.text
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n", "Did not get PNG signature back"
        assert r.headers.get("content-type", "").startswith("image/")

    def test_portfolio_post_requires_admin(self, customer_token):
        r = requests.post(f"{API}/portfolio",
                          json={"title": "no admin", "storage_path": "nosko/portfolio/x.png"},
                          headers={"Authorization": f"Bearer {customer_token}"})
        assert r.status_code == 403, r.text

    @classmethod
    def teardown_class(cls):
        photo_id = getattr(cls, "_photo_id", None)
        if photo_id:
            try:
                tok = _ensure_founder_admin()
                requests.delete(f"{API}/portfolio/{photo_id}",
                                headers={"Authorization": f"Bearer {tok}"})
            except Exception:
                db.portfolio.delete_many({"photo_id": photo_id})
        db.portfolio.delete_many({"title": "TEST_iter7 portfolio"})


# ---------------- Site Settings round-trip with image_path on services ----------------

class TestSiteSettingsServicesImagePath:
    _saved_services = None

    def test_put_site_settings_with_service_image_path_roundtrip(self, admin_token):
        # Snapshot current services list for restoration
        cur = requests.get(f"{API}/site/settings").json()
        TestSiteSettingsServicesImagePath._saved_services = cur.get("services")

        new_services = [
            {"title": "Drywall", "description": "Patch & paint",
             "image_path": "nosko/services/xyz.png"},
            {"title": "Plumbing", "description": "Leaks & swaps",
             "image_path": "nosko/services/plumb.png"},
        ]
        r = requests.put(f"{API}/site/settings",
                         json={"services": new_services},
                         headers={"Authorization": f"Bearer {admin_token}"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "services" in body
        assert len(body["services"]) == 2
        # image_path field must round-trip
        assert body["services"][0]["title"] == "Drywall"
        assert body["services"][0]["image_path"] == "nosko/services/xyz.png"
        assert body["services"][1]["image_path"] == "nosko/services/plumb.png"

        # Subsequent GET should also have the field intact
        g = requests.get(f"{API}/site/settings")
        assert g.status_code == 200
        gsvcs = g.json().get("services", [])
        assert len(gsvcs) == 2
        assert gsvcs[0]["image_path"] == "nosko/services/xyz.png"
        assert gsvcs[1]["image_path"] == "nosko/services/plumb.png"

    @classmethod
    def teardown_class(cls):
        # Restore prior services list to avoid contaminating other tests / UI
        if cls._saved_services is not None:
            try:
                tok = _ensure_founder_admin()
                requests.put(f"{API}/site/settings",
                             json={"services": cls._saved_services},
                             headers={"Authorization": f"Bearer {tok}"})
            except Exception:
                pass
