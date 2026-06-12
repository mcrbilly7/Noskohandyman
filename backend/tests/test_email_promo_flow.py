"""End-to-end tests for the new iteration-5 features:
  - Newsletter subscribers + auto-issued discount codes
  - Discount-code validate + admin CRUD
  - Email templates (defaults seeded, CRUD, single-default invariant)
  - Email blasts preview + send
  - Promo code lifecycle: signup -> create job -> send-quote marks code used -> re-validate says used
"""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://nosko-handyman.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "noskotx@gmail.com"
ADMIN_PASSWORD = "AdminTest12345"


# ---------------------------- Fixtures ----------------------------
@pytest.fixture(scope="session")
def admin_token():
    s = requests.Session()
    # Try login first
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    if r.status_code != 200:
        # Try to register (idempotent for tests)
        s.post(f"{API}/auth/register", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "name": "Nosko Admin"}, timeout=20)
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    data = r.json()
    assert data.get("user", {}).get("role") == "admin", f"Not admin: {data}"
    return data["session_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


def _uniq_email(tag="test"):
    return f"test+{tag}_{uuid.uuid4().hex[:8]}@example.com"


# ---------------------------- Subscribers ----------------------------
class TestSubscribers:
    def test_fresh_signup_returns_code(self):
        email = _uniq_email("sub")
        r = requests.post(f"{API}/subscribers", json={"email": email}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True
        assert isinstance(data.get("code"), str) and len(data["code"]) > 0
        assert data.get("percent_off") == 15
        assert "email_sent" in data

    def test_second_signup_returns_already_subscribed_with_code(self):
        email = _uniq_email("again")
        r1 = requests.post(f"{API}/subscribers", json={"email": email}, timeout=20)
        assert r1.status_code == 200
        code1 = r1.json()["code"]
        r2 = requests.post(f"{API}/subscribers", json={"email": email}, timeout=20)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2.get("already_subscribed") is True
        assert d2.get("code") == code1
        assert d2.get("percent_off") == 15

    def test_invalid_email_rejected(self):
        r = requests.post(f"{API}/subscribers", json={"email": "not-an-email"}, timeout=10)
        assert r.status_code == 400

    def test_list_subscribers_requires_admin(self):
        r = requests.get(f"{API}/subscribers", timeout=10)
        assert r.status_code in (401, 403)

    def test_list_subscribers_hydrated(self, admin_headers):
        email = _uniq_email("list")
        requests.post(f"{API}/subscribers", json={"email": email}, timeout=20)
        r = requests.get(f"{API}/subscribers", headers=admin_headers, timeout=20)
        assert r.status_code == 200
        subs = r.json()
        match = next((s for s in subs if s.get("email") == email), None)
        assert match is not None
        assert match.get("code")
        assert match.get("percent_off") == 15
        assert match.get("code_used") is False
        assert "code_used_on_job_id" in match


# ---------------------------- Discount codes ----------------------------
class TestDiscountCodes:
    def test_validate_garbage(self):
        r = requests.post(f"{API}/discount-codes/validate", json={"code": "ZZZ_NOT_REAL_XYZ"}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["valid"] is False
        assert d["error"] == "Code not found"

    def test_validate_fresh_code(self):
        email = _uniq_email("validate")
        sub = requests.post(f"{API}/subscribers", json={"email": email}, timeout=20).json()
        r = requests.post(f"{API}/discount-codes/validate", json={"code": sub["code"]}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["valid"] is True
        assert d["percent_off"] == 15
        assert d["code"] == sub["code"]

    def test_admin_crud(self, admin_headers):
        # Create
        r = requests.post(f"{API}/discount-codes", json={"percent_off": 20, "notes": "TEST notes"}, headers=admin_headers, timeout=10)
        assert r.status_code == 200, r.text
        doc = r.json()
        code_id = doc["code_id"]
        assert doc["percent_off"] == 20
        assert doc["notes"] == "TEST notes"
        # List
        r = requests.get(f"{API}/discount-codes", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert any(c["code_id"] == code_id for c in r.json())
        # Update percent + notes
        r = requests.put(f"{API}/discount-codes/{code_id}", json={"percent_off": 25, "notes": "updated"}, headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["percent_off"] == 25
        assert r.json()["notes"] == "updated"
        # Delete
        r = requests.delete(f"{API}/discount-codes/{code_id}", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("deleted") == 1

    def test_percent_off_out_of_range(self, admin_headers):
        r = requests.post(f"{API}/discount-codes", json={"percent_off": 0}, headers=admin_headers, timeout=10)
        assert r.status_code == 400
        r = requests.post(f"{API}/discount-codes", json={"percent_off": 101}, headers=admin_headers, timeout=10)
        assert r.status_code == 400

    def test_duplicate_code_rejected(self, admin_headers):
        unique = f"TESTDUP{uuid.uuid4().hex[:6].upper()}"
        r1 = requests.post(f"{API}/discount-codes", json={"percent_off": 10, "code": unique}, headers=admin_headers, timeout=10)
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/discount-codes", json={"percent_off": 10, "code": unique}, headers=admin_headers, timeout=10)
        assert r2.status_code == 409
        # cleanup
        requests.delete(f"{API}/discount-codes/{r1.json()['code_id']}", headers=admin_headers, timeout=10)

    def test_reset_usage(self, admin_headers):
        # Create + manually mark used by walking through full flow is heavy; instead:
        # create, then PUT reset_usage on a freshly created code -> stays unused.
        r = requests.post(f"{API}/discount-codes", json={"percent_off": 5}, headers=admin_headers, timeout=10)
        cid = r.json()["code_id"]
        r2 = requests.put(f"{API}/discount-codes/{cid}", json={"reset_usage": True}, headers=admin_headers, timeout=10)
        assert r2.status_code == 200
        doc = r2.json()
        assert doc.get("used_at") in (None, "")
        assert doc.get("used_on_job_id") in (None, "")
        requests.delete(f"{API}/discount-codes/{cid}", headers=admin_headers, timeout=10)

    def test_admin_endpoints_require_auth(self):
        for verb, url in [
            ("get", f"{API}/discount-codes"),
            ("post", f"{API}/discount-codes"),
            ("put", f"{API}/discount-codes/xxx"),
            ("delete", f"{API}/discount-codes/xxx"),
        ]:
            r = requests.request(verb, url, json={"percent_off": 10}, timeout=10)
            assert r.status_code in (401, 403), f"{verb.upper()} {url} -> {r.status_code}"


# ---------------------------- Email templates ----------------------------
class TestEmailTemplates:
    def test_three_defaults_seeded(self, admin_headers):
        r = requests.get(f"{API}/email-templates", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        tpls = r.json()
        names = {t["name"] for t in tpls}
        # At least the three required ones should exist
        for required in ("Friendly quote", "Formal", "Quick price"):
            assert required in names, f"Missing default template {required}; got {names}"
        # Friendly quote is default
        friendly = next(t for t in tpls if t["name"] == "Friendly quote")
        assert friendly["is_default"] is True
        # Exactly one default overall
        assert sum(1 for t in tpls if t.get("is_default")) == 1

    def test_create_update_delete_and_default_flip(self, admin_headers):
        # Create a new template marked default — should flip Friendly quote off
        new_name = f"TEST tpl {uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/email-templates", json={
            "name": new_name,
            "subject_template": "TEST {{job_id}}",
            "html_template": "<p>Hi {{first_name}} – ${{amount}}</p>",
            "is_default": True,
        }, headers=admin_headers, timeout=10)
        assert r.status_code == 200
        tid = r.json()["template_id"]
        # Verify default flipped
        all_t = requests.get(f"{API}/email-templates", headers=admin_headers, timeout=10).json()
        defaults = [t for t in all_t if t.get("is_default")]
        assert len(defaults) == 1
        assert defaults[0]["template_id"] == tid
        # Update name
        r = requests.put(f"{API}/email-templates/{tid}", json={"name": new_name + " edit"}, headers=admin_headers, timeout=10)
        assert r.status_code == 200 and r.json()["name"] == new_name + " edit"
        # Restore Friendly quote as default for downstream tests
        friendly = next(t for t in all_t if t["name"] == "Friendly quote")
        requests.put(f"{API}/email-templates/{friendly['template_id']}", json={"is_default": True}, headers=admin_headers, timeout=10)
        # Delete TEST tpl
        r = requests.delete(f"{API}/email-templates/{tid}", headers=admin_headers, timeout=10)
        assert r.status_code == 200

    def test_templates_require_auth(self):
        assert requests.get(f"{API}/email-templates", timeout=10).status_code in (401, 403)
        assert requests.post(f"{API}/email-templates", json={"name": "x"}, timeout=10).status_code in (401, 403)


# ---------------------------- E2E: promo lifecycle ----------------------------
class TestPromoLifecycle:
    def test_full_flow_signup_job_send_quote_marks_used(self, admin_headers):
        # 1. Subscribe -> get code
        email = _uniq_email("e2e")
        sub = requests.post(f"{API}/subscribers", json={"email": email}, timeout=20).json()
        code = sub["code"]
        # 2. Validate fresh
        v = requests.post(f"{API}/discount-codes/validate", json={"code": code}, timeout=10).json()
        assert v["valid"] is True
        # 3. Create job with promo_code
        job_payload = {
            "customer_name": "TEST E2E Customer",
            "customer_email": email,
            "address": "123 Test St",
            "service_type": "General Handyman",
            "description": "TEST job for promo lifecycle",
            "promo_code": code,
        }
        rj = requests.post(f"{API}/jobs", json=job_payload, timeout=30)
        assert rj.status_code == 200, rj.text
        job = rj.json()
        assert job["promo_code"] == code
        assert job["promo_meta"]["code"] == code
        assert job["promo_meta"]["percent_off"] == 15
        job_id = job["job_id"]

        # 4. Quote preview with default template + line items
        prev = requests.post(f"{API}/jobs/{job_id}/quote-preview", json={
            "quoted_amount": 250.00,
            "line_items": [{"label": "Labor", "amount": 200}, {"label": "Materials", "amount": 50}],
        }, headers=admin_headers, timeout=15)
        assert prev.status_code == 200, prev.text
        p = prev.json()
        assert "subject" in p and "html" in p
        # Breakdown table should be present
        assert "Labor" in p["html"] and "Materials" in p["html"]
        # Promo strip should appear (yellow promo block)
        assert code in p["html"]

        # 5. Send quote
        send = requests.post(f"{API}/jobs/{job_id}/send-quote", json={
            "quoted_amount": 250.00,
            "line_items": [{"label": "Labor", "amount": 200}, {"label": "Materials", "amount": 50}],
            "subject": p["subject"],
            "html": p["html"],
        }, headers=admin_headers, timeout=30)
        assert send.status_code == 200, send.text
        assert send.json().get("ok") is True

        # 6. Re-validate code -> now used
        time.sleep(0.5)
        v2 = requests.post(f"{API}/discount-codes/validate", json={"code": code}, timeout=10).json()
        assert v2["valid"] is False
        assert v2["error"] == "This code has already been used"

    def test_invalid_promo_silently_dropped(self):
        rj = requests.post(f"{API}/jobs", json={
            "customer_name": "TEST drop", "customer_email": _uniq_email("drop"),
            "address": "1 X", "service_type": "Handyman",
            "promo_code": "NOTAREALCODE_XYZ123",
        }, timeout=20)
        assert rj.status_code == 200
        j = rj.json()
        assert j["promo_code"] is None
        assert j["promo_meta"] is None


# ---------------------------- Email blasts ----------------------------
class TestEmailBlasts:
    def test_preview_returns_recipient_count(self, admin_headers):
        r = requests.post(f"{API}/email-blasts/preview", json={"subject": "TEST", "html": "<p>x</p>"}, headers=admin_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert "recipient_count" in d
        assert isinstance(d["recipient_count"], int)

    def test_list_blasts_requires_auth(self):
        assert requests.get(f"{API}/email-blasts", timeout=10).status_code in (401, 403)

    def test_list_blasts_admin(self, admin_headers):
        r = requests.get(f"{API}/email-blasts", headers=admin_headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_blast_requires_subject_and_body(self, admin_headers):
        r = requests.post(f"{API}/email-blasts", json={"subject": "", "html": ""}, headers=admin_headers, timeout=10)
        assert r.status_code == 400
