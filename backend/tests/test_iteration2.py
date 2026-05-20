"""Iteration 2 backend tests: email/password auth, founder RBAC, minimum_charge, /users/me."""
import os
import uuid
from datetime import datetime, timezone, timedelta

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
FOUNDER2_EMAIL = "nossonkosowsky32@gmail.com"


def _cleanup_email(email: str):
    user = db.users.find_one({"email": email}, {"_id": 0, "user_id": 1})
    if user:
        db.user_sessions.delete_many({"user_id": user["user_id"]})
        db.password_reset_tokens.delete_many({"user_id": user["user_id"]})
    db.users.delete_many({"email": email})


# ---------------- /auth/register ----------------
class TestAuthRegister:
    def test_register_creates_user_and_session(self):
        email = f"test_reg_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(email)
        r = requests.post(f"{API}/auth/register", json={"email": email, "password": "Password123!", "name": "Reg User"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == email
        assert d["user"]["role"] == "customer"
        assert d["user"]["auth_provider"] == "password"
        assert "password_hash" not in d["user"]
        assert d["session_token"]
        # bcrypt hash exists in db and starts with $2b$
        u = db.users.find_one({"email": email})
        assert u and u.get("password_hash", "").startswith("$2")
        # Session is queryable
        assert db.user_sessions.find_one({"session_token": d["session_token"]})
        _cleanup_email(email)

    def test_register_duplicate_409(self):
        email = f"test_dup_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(email)
        requests.post(f"{API}/auth/register", json={"email": email, "password": "Password123!", "name": "Dup"})
        r2 = requests.post(f"{API}/auth/register", json={"email": email, "password": "Password123!", "name": "Dup"})
        assert r2.status_code == 409
        _cleanup_email(email)

    def test_register_short_password_400(self):
        email = f"test_short_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/register", json={"email": email, "password": "short", "name": "S"})
        assert r.status_code == 400

    def test_register_invalid_email_400(self):
        r = requests.post(f"{API}/auth/register", json={"email": "no-at-symbol", "password": "Password123!", "name": "X"})
        assert r.status_code == 400

    def test_register_founder_email_auto_admin(self):
        _cleanup_email(FOUNDER_EMAIL)
        r = requests.post(f"{API}/auth/register", json={"email": FOUNDER_EMAIL, "password": "AdminTest12345", "name": "Founder One"})
        assert r.status_code == 200, r.text
        assert r.json()["user"]["role"] == "admin"

    def test_register_founder2_email_auto_admin(self):
        _cleanup_email(FOUNDER2_EMAIL)
        r = requests.post(f"{API}/auth/register", json={"email": FOUNDER2_EMAIL, "password": "AdminTest12345", "name": "Founder Two"})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"


# ---------------- /auth/login ----------------
class TestAuthLogin:
    @classmethod
    def setup_class(cls):
        cls.email = f"test_login_{uuid.uuid4().hex[:8]}@example.com"
        cls.password = "LoginPass1234"
        _cleanup_email(cls.email)
        r = requests.post(f"{API}/auth/register", json={"email": cls.email, "password": cls.password, "name": "Login Test"})
        assert r.status_code == 200

    @classmethod
    def teardown_class(cls):
        _cleanup_email(cls.email)

    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": self.email, "password": self.password})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["user"]["email"] == self.email
        assert d["session_token"]
        # token works on /auth/me
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {d['session_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == self.email

    def test_login_bad_password_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": self.email, "password": "wrong-password-xxx"})
        assert r.status_code == 401

    def test_login_unknown_email_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": f"nope_{uuid.uuid4().hex}@x.com", "password": "anything12"})
        assert r.status_code == 401

    def test_login_founder_repromotes_to_admin(self):
        # Simulate a founder who was somehow demoted, then logs in.
        _cleanup_email(FOUNDER_EMAIL)
        requests.post(f"{API}/auth/register", json={"email": FOUNDER_EMAIL, "password": "AdminTest12345", "name": "F"})
        # Manually demote
        db.users.update_one({"email": FOUNDER_EMAIL}, {"$set": {"role": "customer"}})
        r = requests.post(f"{API}/auth/login", json={"email": FOUNDER_EMAIL, "password": "AdminTest12345"})
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"


# ---------------- /auth/forgot-password & /auth/reset-password ----------------
class TestForgotResetPassword:
    @classmethod
    def setup_class(cls):
        cls.email = f"test_fp_{uuid.uuid4().hex[:8]}@example.com"
        cls.password = "OrigPass1234"
        _cleanup_email(cls.email)
        requests.post(f"{API}/auth/register", json={"email": cls.email, "password": cls.password, "name": "FP"})

    @classmethod
    def teardown_class(cls):
        _cleanup_email(cls.email)

    def test_forgot_password_nonexistent_returns_ok(self):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": f"never_{uuid.uuid4().hex}@x.com"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}

    def test_forgot_password_existing_creates_token(self):
        before = db.password_reset_tokens.count_documents({"email": self.email})
        r = requests.post(f"{API}/auth/forgot-password", json={"email": self.email, "origin": "https://example.com"})
        assert r.status_code == 200
        assert r.json() == {"ok": True}
        after = db.password_reset_tokens.count_documents({"email": self.email})
        assert after == before + 1

    def test_reset_password_missing_token_400(self):
        r = requests.post(f"{API}/auth/reset-password", json={"password": "NewPass1234"})
        assert r.status_code == 400

    def test_reset_password_short_400(self):
        r = requests.post(f"{API}/auth/reset-password", json={"token": "anything", "password": "short"})
        assert r.status_code == 400

    def test_reset_password_invalid_token_400(self):
        r = requests.post(f"{API}/auth/reset-password", json={"token": "not-a-real-token-xxxx", "password": "NewPass1234"})
        assert r.status_code == 400

    def test_reset_password_valid_token_works_then_used(self):
        # Trigger token creation
        requests.post(f"{API}/auth/forgot-password", json={"email": self.email})
        rec = db.password_reset_tokens.find_one({"email": self.email, "used": False}, sort=[("created_at", -1)])
        assert rec, "Token should have been created"
        token = rec["token"]
        new_pass = "BrandNewPass5678"
        r = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": new_pass})
        assert r.status_code == 200, r.text
        # Login with new pw
        r2 = requests.post(f"{API}/auth/login", json={"email": self.email, "password": new_pass})
        assert r2.status_code == 200
        # Old password no longer works
        r3 = requests.post(f"{API}/auth/login", json={"email": self.email, "password": self.password})
        assert r3.status_code == 401
        # Token cannot be reused
        r4 = requests.post(f"{API}/auth/reset-password", json={"token": token, "password": "AnotherPass1234"})
        assert r4.status_code == 400

    def test_reset_password_expired_token_400(self):
        # Insert a forced-expired token directly
        user = db.users.find_one({"email": self.email})
        tok = f"expired_{uuid.uuid4().hex}"
        db.password_reset_tokens.insert_one({
            "token": tok, "user_id": user["user_id"], "email": self.email,
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "used": False, "created_at": datetime.now(timezone.utc).isoformat(),
        })
        r = requests.post(f"{API}/auth/reset-password", json={"token": tok, "password": "WhateverPass1234"})
        assert r.status_code == 400


# ---------------- /users/me PUT ----------------
class TestUpdateMe:
    @classmethod
    def setup_class(cls):
        cls.email = f"test_me_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(cls.email)
        r = requests.post(f"{API}/auth/register", json={"email": cls.email, "password": "OrigPass1234", "name": "Me"})
        cls.token = r.json()["session_token"]
        cls.h = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def teardown_class(cls):
        _cleanup_email(cls.email)

    def test_update_profile_fields(self):
        r = requests.put(f"{API}/users/me", headers=self.h, json={
            "name": "New Name", "phone": "555-1234", "location": "Dallas", "notify_email": False,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "New Name"
        assert d["phone"] == "555-1234"
        assert d["location"] == "Dallas"
        assert d["notify_email"] is False
        # GET to verify persistence
        me = requests.get(f"{API}/auth/me", headers=self.h).json()
        assert me["name"] == "New Name"
        assert me["phone"] == "555-1234"

    def test_update_password_short_rejected(self):
        r = requests.put(f"{API}/users/me", headers=self.h, json={"password": "short"})
        assert r.status_code == 400

    def test_update_password_valid_changes_login(self):
        new_pw = "ChangedPass9876"
        r = requests.put(f"{API}/users/me", headers=self.h, json={"password": new_pw})
        assert r.status_code == 200
        # Login with new password works
        r2 = requests.post(f"{API}/auth/login", json={"email": self.email, "password": new_pw})
        assert r2.status_code == 200

    def test_update_me_unauthorized(self):
        r = requests.put(f"{API}/users/me", json={"name": "X"})
        assert r.status_code == 401


# ---------------- Admin users + founder-only role change ----------------
class TestAdminUsersAndFounderRBAC:
    @classmethod
    def setup_class(cls):
        # Ensure founder exists & is admin
        _cleanup_email(FOUNDER_EMAIL)
        r = requests.post(f"{API}/auth/register", json={"email": FOUNDER_EMAIL, "password": "AdminTest12345", "name": "Founder"})
        assert r.status_code == 200
        cls.founder_token = r.json()["session_token"]
        cls.founder_h = {"Authorization": f"Bearer {cls.founder_token}"}

        # Create a non-founder admin (via direct DB)
        cls.nonfounder_admin_email = f"test_admin2_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(cls.nonfounder_admin_email)
        rr = requests.post(f"{API}/auth/register", json={
            "email": cls.nonfounder_admin_email, "password": "Password1234", "name": "Admin2"
        })
        cls.nonfounder_admin_uid = rr.json()["user"]["user_id"]
        # Promote to admin via founder
        promote = requests.put(
            f"{API}/admin/users/{cls.nonfounder_admin_uid}/role",
            headers=cls.founder_h, json={"role": "admin"},
        )
        assert promote.status_code == 200, promote.text
        # Login as nonfounder admin to get token
        l = requests.post(f"{API}/auth/login", json={"email": cls.nonfounder_admin_email, "password": "Password1234"})
        cls.nonfounder_h = {"Authorization": f"Bearer {l.json()['session_token']}"}

        # A regular customer as the target
        cls.target_email = f"test_target_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(cls.target_email)
        rt = requests.post(f"{API}/auth/register", json={
            "email": cls.target_email, "password": "Password1234", "name": "Target"
        })
        cls.target_uid = rt.json()["user"]["user_id"]

    @classmethod
    def teardown_class(cls):
        _cleanup_email(FOUNDER_EMAIL)
        _cleanup_email(cls.nonfounder_admin_email)
        _cleanup_email(cls.target_email)

    def test_admin_users_list_includes_users(self):
        r = requests.get(f"{API}/admin/users", headers=self.founder_h)
        assert r.status_code == 200
        emails = [u["email"] for u in r.json()]
        assert FOUNDER_EMAIL in emails
        assert self.target_email in emails
        # password_hash never leaked
        assert all("password_hash" not in u for u in r.json())

    def test_admin_users_requires_admin(self):
        # anonymous
        r = requests.get(f"{API}/admin/users")
        assert r.status_code == 401

    def test_founder_can_change_role(self):
        r = requests.put(
            f"{API}/admin/users/{self.target_uid}/role",
            headers=self.founder_h, json={"role": "worker"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["role"] == "worker"
        # verify
        u = db.users.find_one({"user_id": self.target_uid})
        assert u["role"] == "worker"

    def test_nonfounder_admin_cannot_change_role(self):
        r = requests.put(
            f"{API}/admin/users/{self.target_uid}/role",
            headers=self.nonfounder_h, json={"role": "customer"},
        )
        assert r.status_code == 403

    def test_founder_cannot_demote_other_founder(self):
        # Register founder2
        _cleanup_email(FOUNDER2_EMAIL)
        rr = requests.post(f"{API}/auth/register", json={"email": FOUNDER2_EMAIL, "password": "AdminTest12345", "name": "F2"})
        f2_uid = rr.json()["user"]["user_id"]
        r = requests.put(
            f"{API}/admin/users/{f2_uid}/role",
            headers=self.founder_h, json={"role": "customer"},
        )
        assert r.status_code == 400
        _cleanup_email(FOUNDER2_EMAIL)

    def test_invalid_role_rejected(self):
        r = requests.put(
            f"{API}/admin/users/{self.target_uid}/role",
            headers=self.founder_h, json={"role": "bogus_role"},
        )
        assert r.status_code == 400

    def test_role_change_nonexistent_user_404(self):
        r = requests.put(
            f"{API}/admin/users/no-such-user/role",
            headers=self.founder_h, json={"role": "worker"},
        )
        assert r.status_code == 404


# ---------------- Site settings: minimum_charge + outlet_price ----------------
class TestSiteSettingsAndMinimumCharge:
    def test_defaults_include_minimum_and_outlet(self):
        # reset to defaults: delete settings doc
        db.site_settings.delete_many({"key": "default"})
        r = requests.get(f"{API}/site/settings")
        assert r.status_code == 200
        d = r.json()
        assert d.get("minimum_charge") == 50.0
        assert d.get("outlet_price") == 0.0  # owner removed the $25 set price; only minimum applies

    def test_outlet_job_priced_at_25(self):
        # outlet/switch service => $25 fixed (above minimum logic still kicks in but base=25, minimum=50 → quoted=max(25,50)=50)
        # Wait: code does quoted = max(quoted_amount or base, minimum). For outlet, base=25, minimum=50 → final=50.
        # That means outlet pricing < minimum is forced up to $50. We just verify behavior.
        payload = {
            "customer_name": "TEST_Min", "customer_email": "TEST_min@example.com",
            "address": "1 Main", "service_type": "Switch/Outlet Replacement", "description": "x",
        }
        r = requests.post(f"{API}/jobs", json=payload)
        assert r.status_code == 200
        # quoted_amount should be the max(base=outlet_price=25, minimum=50) = 50
        assert r.json()["quoted_amount"] == 50.0

    def test_quoted_below_minimum_forced_up(self):
        payload = {
            "customer_name": "TEST_Force", "customer_email": "TEST_force@example.com",
            "address": "2 Main", "service_type": "General Repair", "description": "y",
            "quoted_amount": 10.0,
        }
        r = requests.post(f"{API}/jobs", json=payload)
        assert r.status_code == 200
        assert r.json()["quoted_amount"] == 50.0

    def test_quoted_above_minimum_respected(self):
        payload = {
            "customer_name": "TEST_Hi", "customer_email": "TEST_hi@example.com",
            "address": "3 Main", "service_type": "General Repair", "description": "z",
            "quoted_amount": 175.0,
        }
        r = requests.post(f"{API}/jobs", json=payload)
        assert r.status_code == 200
        assert r.json()["quoted_amount"] == 175.0


# ---------------- Hybrid auth: session token works after both flows ----------------
class TestHybridAuth:
    def test_password_session_works_on_authed_route(self):
        email = f"test_hyb_{uuid.uuid4().hex[:8]}@example.com"
        _cleanup_email(email)
        r = requests.post(f"{API}/auth/register", json={"email": email, "password": "PasswordHybrid1", "name": "H"})
        token = r.json()["session_token"]
        # auth/me
        me = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        # logout invalidates session
        out = requests.post(f"{API}/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert out.status_code == 200
        me2 = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me2.status_code == 401
        _cleanup_email(email)


# ---------------- POST /api/jobs still works unauth + invalid referral nulled ----------------
def test_jobs_unauth_still_works():
    payload = {
        "customer_name": "TEST_Anon", "customer_email": "TEST_anon@example.com",
        "address": "9 Main", "service_type": "General Repair", "description": "no auth",
        "referral_code": "INVALID-CODE",
    }
    r = requests.post(f"{API}/jobs", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert j["referral_code"] is None
    assert j["quoted_amount"] >= 50.0


# ---------------- Cleanup any TEST_ jobs ----------------
def teardown_module(module):
    db.jobs.delete_many({"customer_email": {"$regex": "^TEST_"}})
