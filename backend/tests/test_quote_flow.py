"""
Backend tests for manual quote workflow (iteration 4).
Covers:
- POST /api/jobs creates job with quoted_amount=null, quote_status='pending' (no auto-pricing)
- GET /api/jobs/track/{id} returns null quoted_amount without crashing
- PUT /api/jobs/{id}/quote saves price, sets quote_status='draft' (admin auth)
- POST /api/jobs/{id}/quote-preview returns subject/html/text (admin auth)
- POST /api/jobs/{id}/send-quote sends email, sets quote_status='sent' (admin auth)
- Auth required on all 4 admin endpoints (401 without token)
"""
import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nosko-handyman.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "noskotx@gmail.com"
ADMIN_PASSWORD = "AdminTest12345"


@pytest.fixture(scope="module")
def admin_token():
    """Login or register admin (auto-promoted via FOUNDING_ADMINS)."""
    s = requests.Session()
    # Try login first
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        # Register if not exists
        rr = s.post(f"{API}/auth/register", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Nosko Admin"
        }, timeout=15)
        if rr.status_code not in (200, 201):
            # Try login again - maybe race
            r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
            assert r.status_code == 200, f"Auth failed: {r.status_code} {r.text}"
            data = r.json()
        else:
            data = rr.json()
    else:
        data = r.json()
    token = data.get("session_token")
    assert token, f"No session_token in auth response: {data}"
    assert data["user"].get("role") in ("admin", "developer"), f"Admin not promoted: {data['user']}"
    return token


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


@pytest.fixture
def fresh_job():
    """Create a fresh anonymous job for testing the quote flow."""
    payload = {
        "customer_name": "TEST Quote Customer",
        "customer_email": "test_quote@example.com",
        "customer_phone": "555-0100",
        "address": "123 Test Lane, Dallas TX",
        "service_type": "Other / Custom job",
        "description": "TEST job for quote-flow pytest"
    }
    r = requests.post(f"{API}/jobs", json=payload, timeout=20)
    assert r.status_code == 200, f"Create job failed: {r.status_code} {r.text}"
    return r.json()


# ---------------- 1. Create job: no auto-pricing ----------------
class TestCreateJob:
    def test_create_job_no_auto_price(self, fresh_job):
        """Job must be created with quoted_amount=None and quote_status='pending'."""
        assert fresh_job["quoted_amount"] is None, f"Expected None, got {fresh_job.get('quoted_amount')}"
        assert fresh_job["quote_status"] == "pending"
        assert fresh_job.get("quote_sent_at") is None
        assert fresh_job["job_id"].startswith("job_")

    def test_create_job_does_not_crash_on_smtp_fail(self):
        """Anonymous create-job must succeed even if SMTP fails (fire-and-forget)."""
        r = requests.post(f"{API}/jobs", json={
            "customer_name": "TEST SMTP Resilience",
            "customer_email": "test_smtp@example.com",
            "address": "456 SMTP St",
            "service_type": "Other / Custom job",
            "description": "fire-and-forget email check"
        }, timeout=20)
        assert r.status_code == 200, f"Job create failed when SMTP may be broken: {r.text}"
        body = r.json()
        assert body["quoted_amount"] is None
        assert body["quote_status"] == "pending"


# ---------------- 2. Track endpoint handles null amount ----------------
class TestTrackJob:
    def test_track_returns_null_for_pending(self, fresh_job):
        r = requests.get(f"{API}/jobs/track/{fresh_job['job_id']}", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quoted_amount"] is None
        assert body["quote_status"] == "pending"
        assert "eta_message" in body

    def test_track_404_unknown_job(self):
        r = requests.get(f"{API}/jobs/track/job_nonexistent_xyz", timeout=10)
        assert r.status_code == 404


# ---------------- 3. Auth-required endpoints ----------------
class TestQuoteAuthRequired:
    def test_save_quote_requires_auth(self, fresh_job):
        r = requests.put(f"{API}/jobs/{fresh_job['job_id']}/quote",
                         json={"quoted_amount": 100}, timeout=10)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_preview_requires_auth(self, fresh_job):
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/quote-preview",
                          json={"quoted_amount": 100}, timeout=10)
        assert r.status_code in (401, 403)

    def test_send_quote_requires_auth(self, fresh_job):
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/send-quote",
                          json={"quoted_amount": 100}, timeout=10)
        assert r.status_code in (401, 403)


# ---------------- 4. PUT /jobs/{id}/quote ----------------
class TestSaveQuote:
    def test_save_quote_sets_draft(self, fresh_job, admin_headers):
        r = requests.put(f"{API}/jobs/{fresh_job['job_id']}/quote",
                         json={"quoted_amount": 175.50}, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quoted_amount"] == 175.50
        assert body["quote_status"] == "draft"
        # Public track endpoint must NOT leak the draft price (only 'sent' quotes go public)
        g = requests.get(f"{API}/jobs/track/{fresh_job['job_id']}", timeout=10)
        assert g.status_code == 200
        assert g.json()["quoted_amount"] is None
        assert g.json()["quote_status"] == "draft"

    def test_save_quote_invalid_amount(self, fresh_job, admin_headers):
        r = requests.put(f"{API}/jobs/{fresh_job['job_id']}/quote",
                         json={"quoted_amount": "not-a-number"}, headers=admin_headers, timeout=10)
        assert r.status_code == 400

    def test_save_quote_negative_rejected(self, fresh_job, admin_headers):
        r = requests.put(f"{API}/jobs/{fresh_job['job_id']}/quote",
                         json={"quoted_amount": -50}, headers=admin_headers, timeout=10)
        assert r.status_code == 400

    def test_save_quote_404(self, admin_headers):
        r = requests.put(f"{API}/jobs/job_nope_xyz/quote",
                         json={"quoted_amount": 100}, headers=admin_headers, timeout=10)
        assert r.status_code == 404


# ---------------- 5. POST /jobs/{id}/quote-preview ----------------
class TestQuotePreview:
    def test_preview_returns_template(self, fresh_job, admin_headers):
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/quote-preview",
                          json={"quoted_amount": 250.00}, headers=admin_headers, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "subject" in body and isinstance(body["subject"], str) and body["subject"]
        assert "html" in body and isinstance(body["html"], str) and body["html"]
        assert "text" in body and isinstance(body["text"], str) and body["text"]
        # Should reference the customer or job
        assert fresh_job["job_id"] in body["subject"] or fresh_job["customer_name"].split()[0] in body["html"]
        # Amount should appear formatted
        assert "250" in body["html"] or "250.00" in body["html"]

    def test_preview_invalid_amount(self, fresh_job, admin_headers):
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/quote-preview",
                          json={}, headers=admin_headers, timeout=10)
        assert r.status_code == 400


# ---------------- 6. POST /jobs/{id}/send-quote ----------------
class TestSendQuote:
    def test_send_quote_full_flow(self, fresh_job, admin_headers):
        # First preview to get template
        prev = requests.post(f"{API}/jobs/{fresh_job['job_id']}/quote-preview",
                             json={"quoted_amount": 300}, headers=admin_headers, timeout=15)
        assert prev.status_code == 200
        template = prev.json()

        # Then send
        send_payload = {
            "quoted_amount": 300,
            "subject": template["subject"],
            "html": template["html"],
            "text": template["text"],
        }
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/send-quote",
                          json=send_payload, headers=admin_headers, timeout=30)
        if r.status_code == 502:
            # SMTP not configured in preview env — acceptable per spec.
            # Verify DB record was NOT updated to 'sent'.
            g = requests.get(f"{API}/jobs/track/{fresh_job['job_id']}", timeout=10)
            assert g.json()["quote_status"] != "sent", \
                "DB should not mark sent when SMTP fails"
            pytest.skip(f"SMTP not configured (502). Endpoint shape OK. Body: {r.text[:200]}")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert "quote_sent_at" in body
        assert body["to"] == fresh_job["customer_email"]

        # Verify persistence
        time.sleep(0.5)
        g = requests.get(f"{API}/jobs/track/{fresh_job['job_id']}", timeout=10)
        assert g.status_code == 200
        gb = g.json()
        assert gb["quote_status"] == "sent"
        assert gb["quoted_amount"] == 300
        assert gb["quote_sent_at"] is not None

    def test_send_quote_invalid_amount(self, fresh_job, admin_headers):
        r = requests.post(f"{API}/jobs/{fresh_job['job_id']}/send-quote",
                          json={"subject": "x", "html": "y"}, headers=admin_headers, timeout=10)
        assert r.status_code == 400

    def test_send_quote_404(self, admin_headers):
        r = requests.post(f"{API}/jobs/job_nonexistent/send-quote",
                          json={"quoted_amount": 100}, headers=admin_headers, timeout=10)
        assert r.status_code == 404
