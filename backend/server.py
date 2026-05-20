"""Nosko Handyman backend - FastAPI + MongoDB.
Hybrid auth: Emergent Google OAuth + custom email/password (bcrypt + session tokens).
Emergent object storage for uploads. Gmail SMTP for transactional emails.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, Header, Cookie, Response, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Literal
from pathlib import Path
from datetime import datetime, timezone, timedelta
import os
import uuid
import logging
import secrets
import string
import smtplib
import bcrypt
import stripe
import requests as http_requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
FOUNDING_ADMINS_LIST = [e.strip().lower() for e in os.environ.get("FOUNDING_ADMINS", "").split(",") if e.strip()]
FOUNDING_ADMINS = set(FOUNDING_ADMINS_LIST)
COMPANY_EMAIL = os.environ.get("COMPANY_EMAIL", "noskotx@gmail.com")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
APP_NAME = "nosko"

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Nosko Handyman")
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Nosko Handyman API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nosko")


# -------------------- Email --------------------
def send_email(to: str, subject: str, html: str, text: Optional[str] = None) -> bool:
    """Send via Gmail SMTP. Returns True/False; never raises."""
    if not (SMTP_USER and SMTP_PASSWORD):
        logger.warning("SMTP credentials missing - email not sent")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((SMTP_FROM_NAME, SMTP_USER))
        msg["To"] = to
        if text:
            msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASSWORD)
            s.sendmail(SMTP_USER, [to], msg.as_string())
        logger.info(f"Email sent → {to}")
        return True
    except Exception as e:
        logger.error(f"Email send failed → {to}: {e}")
        return False


def email_welcome(to: str, name: str):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
      <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
        <h1 style="margin:0;font-size:28px;letter-spacing:-1px">NOSKO HANDYMAN</h1>
      </div>
      <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
        <h2 style="margin:0 0 12px">Welcome, {name}.</h2>
        <p>Your account is live. We service the <b>DFW Metroplex</b>. Switch / outlet replacement is fixed at <b>$25</b>. Minimum on any job is <b>$50</b>.</p>
        <p>Questions? Reply to this email.</p>
        <p style="margin-top:24px;font-size:12px;color:#666">— Nosko Handyman Co. · noskotx@gmail.com</p>
      </div>
    </div>
    """
    send_email(to, "Welcome to Nosko Handyman", html, f"Welcome, {name}. Your Nosko account is live.")


def email_quote_to_admin(job: dict):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto">
      <div style="background:#0A0A0A;color:#FFD600;padding:18px 24px">
        <h2 style="margin:0">NEW JOB REQUEST · {job['job_id']}</h2>
      </div>
      <div style="padding:20px;border:1px solid #ddd;border-top:0">
        <p><b>From:</b> {job['customer_name']} &lt;{job['customer_email']}&gt;</p>
        <p><b>Phone:</b> {job.get('customer_phone') or '—'}</p>
        <p><b>Service:</b> {job['service_type']}</p>
        <p><b>Address:</b> {job['address']}</p>
        <p><b>Description:</b><br>{job['description']}</p>
        <p><b>Quoted:</b> ${job['quoted_amount']:.2f}</p>
        {'<p><b>Referral:</b> ' + job['referral_code'] + '</p>' if job.get('referral_code') else ''}
        <p><b>Photos uploaded:</b> {len(job.get('photo_paths', []))}</p>
      </div>
    </div>
    """
    send_email(COMPANY_EMAIL, f"New quote request — {job['customer_name']}", html)


def email_quote_to_customer(job: dict, origin: Optional[str] = None):
    track_url = f"{origin or 'https://nosko.com'}/track/{job['job_id']}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
      <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
        <h1 style="margin:0;font-size:24px">REQUEST RECEIVED</h1>
      </div>
      <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
        <p>Hey {job['customer_name']},</p>
        <p>We got your request <b>{job['job_id']}</b> for <b>{job['service_type']}</b> at {job['address']}.</p>
        <p>A handyman from our DFW team will be in touch shortly.</p>
        <p style="margin:24px 0"><a href="{track_url}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">TRACK YOUR JOB</a></p>
        <p style="font-size:12px;color:#666">No login needed. Bookmark the link to check status anytime.</p>
        <p>— Nosko Handyman · {COMPANY_EMAIL}</p>
      </div>
    </div>
    """
    send_email(job['customer_email'], "Your Nosko quote request", html)


def email_reset_link(to: str, name: str, link: str):
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
      <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
        <h1 style="margin:0;font-size:22px">PASSWORD RESET</h1>
      </div>
      <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
        <p>Hi {name},</p>
        <p>Click the button below to set a new password. This link expires in 1 hour.</p>
        <p style="margin:24px 0"><a href="{link}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">RESET PASSWORD</a></p>
        <p style="font-size:12px;color:#666">Didn't request this? Ignore the email.</p>
      </div>
    </div>
    """
    send_email(to, "Reset your Nosko password", html, f"Reset your Nosko password: {link}")


# -------------------- Storage --------------------
_storage_key: Optional[str] = None


def init_storage() -> Optional[str]:
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_LLM_KEY:
        return None
    try:
        r = http_requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        _storage_key = None
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(503, "Storage unavailable")
    r = http_requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    r.raise_for_status()
    return r.json()


def get_object(path: str):
    key = init_storage()
    if not key:
        raise HTTPException(503, "Storage unavailable")
    r = http_requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


# -------------------- Models --------------------
class SiteSettings(BaseModel):
    # Hero
    hero_title: str = "Full handyman service, fixed honest pricing."
    hero_subtitle: str = "Free quote in 24 hrs. $50 minimum per visit (covers travel + diagnosis). DFW Metroplex."
    cta_primary_label: str = "Get a free quote"
    cta_secondary_label: str = "See what we do"

    # Contact / brand
    contact_phone: str = "(555) 123-4567"
    contact_email: str = "noskotx@gmail.com"
    service_area: str = "DFW Metroplex"
    minimum_charge: float = 50.0
    outlet_price: float = 0.0  # 0 = hidden on landing/request pages
    website_domain: str = "noskotx.com"

    # Section headings
    services_overline: str = "What we fix"
    services_heading: str = "Anything a handyman does — we do."
    services_subheading: str = ""
    how_overline: str = "How it works"
    how_heading: str = "Three steps. Zero phone tag."
    programs_overline: str = "Work with us"
    programs_heading: str = "Earn with Nosko."
    final_cta_overline: str = "Ready to book?"
    final_cta_heading: str = "Send a photo. Get a quote."
    final_cta_label: str = "Request now"

    # Lists
    services: List[dict] = [
        {"title": "Electrical small jobs", "description": "Switches, outlets, fixtures, simple wiring."},
        {"title": "Plumbing fixes", "description": "Faucets, leaks, toilet swaps, garbage disposals."},
        {"title": "Drywall & paint", "description": "Patch holes, retouch, full rooms — quoted."},
        {"title": "Carpentry & install", "description": "Doors, shelves, mounts, appliance install."},
        {"title": "Tile & flooring", "description": "Repairs, replacements, transitions."},
        {"title": "Outdoor & yard", "description": "Fence patch, deck boards, light landscaping."},
        {"title": "Furniture assembly", "description": "Flat-pack, mounts, brackets — quick & clean."},
        {"title": "Other", "description": "If a handyman does it, we do it. Just ask."},
    ]
    how_it_works: List[dict] = [
        {"title": "Send a photo", "description": "Upload a picture of the job. Add the address."},
        {"title": "Get a quote", "description": "We reply with a fixed-price quote — fast."},
        {"title": "Job done", "description": "$50 minimum per visit. No surprises. Pay when complete."},
    ]

    # Programs
    worker_program_title: str = "Handymen wanted"
    worker_program_body: str = "Set your hours. Pick your skills. W9 / 1099 with weekly payouts and a full earnings dashboard."
    worker_program_cta: str = "Apply as handyman"
    marketer_program_title: str = "Marketer program — 15% share"
    marketer_program_body: str = "Sign up, get a personal referral code. Every booking with your code earns you 15% — paid weekly."
    marketer_program_cta: str = "Join as marketer"

    # Footer
    footer_tagline: str = "Full-service handyman based in the DFW Metroplex. $50 minimum per visit. W9 / 1099 compliant."


# -------------------- Helpers --------------------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def gen_referral_code(name: str) -> str:
    base = "".join(c for c in (name or "NOSKO").upper() if c.isalpha())[:4] or "NOSKO"
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    return f"{base}-{suffix}"


def new_session_token() -> str:
    return secrets.token_urlsafe(48)


def role_for_email(email: str, default: str = "customer") -> str:
    return "admin" if email.lower() in FOUNDING_ADMINS else default


def serialize_user(u: dict) -> dict:
    u = dict(u)
    u.pop("_id", None)
    u.pop("password_hash", None)
    return u


async def create_session(user_id: str, token: Optional[str] = None) -> str:
    token = token or new_session_token()
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return token


def set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key="session_token", value=token, httponly=True, secure=True,
        samesite="none", path="/", max_age=7 * 24 * 60 * 60,
    )


async def get_session_token(authorization: Optional[str] = Header(None), session_token: Optional[str] = Cookie(None)) -> Optional[str]:
    if session_token:
        return session_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


async def get_current_user(token: Optional[str] = Depends(get_session_token)) -> dict:
    if not token:
        raise HTTPException(401, "Not authenticated")
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        raise HTTPException(401, "Invalid session")
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(401, "Session expired")
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") not in ("admin", "developer"):
        raise HTTPException(403, "Admin only")
    return user


async def require_founder(user: dict = Depends(get_current_user)) -> dict:
    if user.get("email", "").lower() not in FOUNDING_ADMINS:
        raise HTTPException(403, "Founder only")
    return user


# -------------------- Auth: email/password --------------------
@api.post("/auth/register")
async def register(payload: dict):
    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip() or email.split("@")[0]
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(409, "Email already registered")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    role = role_for_email(email)
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": None,
        "role": role,
        "password_hash": hash_password(password),
        "phone": None,
        "location": None,
        "notify_email": True,
        "auth_provider": "password",
        "referral_code": None,
        "created_at": now,
    })
    token = await create_session(user_id)
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    # welcome email (non-blocking failure)
    email_welcome(email, name)
    resp = JSONResponse({"user": user_doc, "session_token": token})
    set_session_cookie(resp, token)
    return resp


@api.post("/auth/login")
async def login(payload: dict):
    email = (payload.get("email") or "").lower().strip()
    password = payload.get("password") or ""
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    # Re-promote if email is a founder
    if email in FOUNDING_ADMINS and user.get("role") != "admin":
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": "admin"}})
        user["role"] = "admin"
    token = await create_session(user["user_id"])
    user_doc = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    resp = JSONResponse({"user": user_doc, "session_token": token})
    set_session_cookie(resp, token)
    return resp


@api.post("/auth/forgot-password")
async def forgot_password(payload: dict, request: Request):
    email = (payload.get("email") or "").lower().strip()
    origin = payload.get("origin") or str(request.base_url).rstrip("/")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if user and user.get("password_hash"):
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "email": email,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        link = f"{origin}/reset-password?token={token}"
        email_reset_link(email, user.get("name") or email, link)
    # Always return ok to avoid leaking which emails exist
    return {"ok": True}


@api.post("/auth/reset-password")
async def reset_password(payload: dict):
    token = payload.get("token")
    new_password = payload.get("password") or ""
    if not token:
        raise HTTPException(400, "Token required")
    if len(new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    rec = await db.password_reset_tokens.find_one({"token": token, "used": False}, {"_id": 0})
    if not rec:
        raise HTTPException(400, "Invalid or expired token")
    expires_at = rec["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired")
    await db.users.update_one({"user_id": rec["user_id"]}, {"$set": {"password_hash": hash_password(new_password)}})
    await db.password_reset_tokens.update_one({"token": token}, {"$set": {"used": True}})
    return {"ok": True}


# -------------------- Auth: Emergent OAuth --------------------
@api.post("/auth/session")
async def auth_session(payload: dict):
    """Exchange Emergent session_id for our internal session_token."""
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(400, "session_id required")
    try:
        r = http_requests.get(EMERGENT_AUTH_URL, headers={"X-Session-ID": session_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.error(f"Emergent auth failed: {e}")
        raise HTTPException(401, "Auth exchange failed")

    email = data["email"].lower()
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    is_new = False
    if existing:
        user_id = existing["user_id"]
        update = {"name": data.get("name", existing.get("name")), "picture": data.get("picture")}
        if email in FOUNDING_ADMINS and existing.get("role") != "admin":
            update["role"] = "admin"
        await db.users.update_one({"user_id": user_id}, {"$set": update})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name", email),
            "picture": data.get("picture"),
            "role": role_for_email(email),
            "auth_provider": "google",
            "phone": None,
            "location": None,
            "notify_email": True,
            "referral_code": None,
            "created_at": now,
        })
        is_new = True

    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": now,
    })
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if is_new:
        email_welcome(email, user_doc.get("name") or email)
    resp = JSONResponse({"user": user_doc, "session_token": session_token})
    set_session_cookie(resp, session_token)
    return resp


@api.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    return serialize_user(user)


@api.post("/auth/logout")
async def auth_logout(token: Optional[str] = Depends(get_session_token)):
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session_token", path="/")
    return resp


# -------------------- Account settings --------------------
@api.put("/users/me")
async def update_me(payload: dict, user: dict = Depends(get_current_user)):
    update = {}
    for k in ("name", "phone", "location", "notify_email"):
        if k in payload:
            update[k] = payload[k]
    if "password" in payload and payload["password"]:
        if len(payload["password"]) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        update["password_hash"] = hash_password(payload["password"])
    if update:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": update})
    new_user = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return new_user


# -------------------- Role/profile setup --------------------
@api.post("/workers/signup")
async def worker_signup(payload: dict, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    profile = {
        "user_id": user["user_id"],
        "hours_per_week": payload.get("hours_per_week"),
        "skills": payload.get("skills", []),
        "location": payload.get("location"),
        "phone": payload.get("phone"),
        "bio": payload.get("bio"),
        "stripe_account_id": None,
        "created_at": now,
    }
    await db.worker_profiles.update_one({"user_id": user["user_id"]}, {"$set": profile}, upsert=True)
    if user.get("role") in ("customer", None):
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": "worker"}})
    return {"ok": True, "profile": profile}


@api.get("/workers/me")
async def worker_me(user: dict = Depends(get_current_user)):
    profile = await db.worker_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return profile or {}


@api.get("/workers")
async def list_workers(_: dict = Depends(require_admin)):
    workers = await db.worker_profiles.find({}, {"_id": 0}).to_list(1000)
    for w in workers:
        u = await db.users.find_one({"user_id": w["user_id"]}, {"_id": 0, "password_hash": 0})
        w["user"] = u
    return workers


@api.post("/marketers/signup")
async def marketer_signup(payload: dict, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    code = user.get("referral_code")
    if not code:
        for _ in range(5):
            candidate = gen_referral_code(user.get("name", "NOSKO"))
            exists = await db.users.find_one({"referral_code": candidate}, {"_id": 0})
            if not exists:
                code = candidate
                break
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"referral_code": code}})
    profile = {
        "user_id": user["user_id"],
        "referral_code": code,
        "phone": payload.get("phone"),
        "location": payload.get("location"),
        "stripe_account_id": None,
        "created_at": now,
    }
    await db.marketer_profiles.update_one({"user_id": user["user_id"]}, {"$set": profile}, upsert=True)
    if user.get("role") in ("customer", None):
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"role": "marketer"}})
    return {"ok": True, "referral_code": code, "profile": profile}


@api.get("/marketers/me")
async def marketer_me(user: dict = Depends(get_current_user)):
    profile = await db.marketer_profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return profile or {}


@api.get("/marketers")
async def list_marketers(_: dict = Depends(require_admin)):
    marketers = await db.marketer_profiles.find({}, {"_id": 0}).to_list(1000)
    for m in marketers:
        u = await db.users.find_one({"user_id": m["user_id"]}, {"_id": 0, "password_hash": 0})
        m["user"] = u
        m["referral_count"] = await db.jobs.count_documents({"referral_code": m["referral_code"]})
    return marketers


@api.get("/referral/{code}")
async def referral_check(code: str):
    u = await db.users.find_one({"referral_code": code.upper()}, {"_id": 0, "name": 1, "referral_code": 1})
    if not u:
        return {"valid": False}
    return {"valid": True, "marketer_name": u.get("name")}


# -------------------- Team (founder-only) --------------------
@api.get("/admin/users")
async def list_all_users(_: dict = Depends(require_admin)):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
    return users


@api.put("/admin/users/{user_id}/role")
async def set_user_role(user_id: str, payload: dict, founder: dict = Depends(require_founder)):
    role = payload.get("role")
    if role not in ("customer", "worker", "marketer", "developer", "admin"):
        raise HTTPException(400, "Invalid role")
    target = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    if not target:
        raise HTTPException(404, "User not found")
    # Founders cannot be demoted by other founders accidentally — block role change on founder emails
    if target.get("email", "").lower() in FOUNDING_ADMINS and role != "admin":
        raise HTTPException(400, "Cannot change role of founding admin")
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": role}})
    return {"ok": True, "user_id": user_id, "role": role}


# -------------------- W9 --------------------
@api.post("/w9/sign")
async def w9_sign(payload: dict, user: dict = Depends(get_current_user)):
    record = {
        "user_id": user["user_id"],
        "full_legal_name": payload["full_legal_name"],
        "business_name": payload.get("business_name"),
        "ssn_or_ein": payload["ssn_or_ein"],
        "address": payload["address"],
        "tax_classification": payload.get("tax_classification", "individual"),
        "typed_signature": payload["typed_signature"],
        "pdf_path": payload.get("pdf_path"),
        "signed_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.w9_records.update_one({"user_id": user["user_id"]}, {"$set": record}, upsert=True)
    return {"ok": True}


@api.get("/w9/me")
async def w9_me(user: dict = Depends(get_current_user)):
    rec = await db.w9_records.find_one({"user_id": user["user_id"]}, {"_id": 0, "ssn_or_ein": 0})
    return rec or {}


# -------------------- Files --------------------
@api.post("/upload")
async def upload(file: UploadFile = File(...), folder: str = Form("misc")):
    ext = (file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "bin").lower()
    safe_folder = "".join(c for c in folder if c.isalnum() or c in ("-", "_")) or "misc"
    path = f"{APP_NAME}/{safe_folder}/{uuid.uuid4().hex}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "application/octet-stream")
    await db.files.insert_one({
        "id": str(uuid.uuid4()),
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size"),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"path": result["path"]}


@api.get("/files/{path:path}")
async def download(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ctype = get_object(path)
    return Response(content=data, media_type=rec.get("content_type") or ctype)


# -------------------- Jobs --------------------
@api.post("/jobs")
async def create_job(payload: dict, request: Request):
    now = datetime.now(timezone.utc).isoformat()
    referral_code = (payload.get("referral_code") or "").upper().strip() or None
    if referral_code:
        ref = await db.users.find_one({"referral_code": referral_code}, {"_id": 0})
        if not ref:
            referral_code = None
    # Reject job if preferred_date is on a blocked day
    pdate = (payload.get("preferred_date") or "").strip() or None
    if pdate:
        avail = await db.availability.find_one({"key": "default"}, {"_id": 0, "blocked_dates": 1})
        blocked = (avail or {}).get("blocked_dates", [])
        if pdate in blocked:
            raise HTTPException(400, "Selected date is unavailable. Please pick another day.")
    settings_doc = await db.site_settings.find_one({"key": "default"}, {"_id": 0, "key": 0})
    minimum = float((settings_doc or {}).get("minimum_charge", 50.0))
    service_type = payload.get("service_type", "General Handyman")
    quoted = max(float(payload.get("quoted_amount") or minimum), minimum)
    job = {
        "job_id": f"job_{uuid.uuid4().hex[:10]}",
        "customer_name": payload["customer_name"],
        "customer_email": payload["customer_email"],
        "customer_phone": payload.get("customer_phone"),
        "address": payload["address"],
        "service_type": service_type,
        "description": payload.get("description", ""),
        "photo_paths": payload.get("photo_paths", []),
        "referral_code": referral_code,
        "preferred_date": payload.get("preferred_date"),
        "preferred_time_slot": payload.get("preferred_time_slot"),
        "quoted_amount": quoted,
        "status": "new",
        "assigned_worker_id": None,
        "created_at": now,
    }
    await db.jobs.insert_one(job)
    job.pop("_id", None)
    # Fire-and-forget emails (sync — but small)
    try:
        email_quote_to_admin(job)
        origin = payload.get("origin") or request.headers.get("origin") or str(request.base_url).rstrip("/")
        email_quote_to_customer(job, origin)
    except Exception as e:
        logger.error(f"Email dispatch failed for {job['job_id']}: {e}")
    return job


@api.get("/jobs")
async def list_jobs(_: dict = Depends(require_admin)):
    jobs = await db.jobs.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return jobs


@api.get("/jobs/me")
async def my_jobs(user: dict = Depends(get_current_user)):
    jobs = await db.jobs.find({"assigned_worker_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return jobs


@api.put("/jobs/{job_id}/assign")
async def assign_job(job_id: str, payload: dict, _: dict = Depends(require_admin)):
    worker_id = payload.get("worker_id")
    if not worker_id:
        raise HTTPException(400, "worker_id required")
    res = await db.jobs.update_one({"job_id": job_id}, {"$set": {"assigned_worker_id": worker_id, "status": "assigned"}})
    if res.matched_count == 0:
        raise HTTPException(404, "Job not found")
    return {"ok": True}


@api.get("/jobs/track/{job_id}")
async def track_job(job_id: str):
    """Public endpoint — no auth. Returns safe subset of job info for the customer's tracking page."""
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    worker_name = None
    if job.get("assigned_worker_id"):
        w = await db.users.find_one({"user_id": job["assigned_worker_id"]}, {"_id": 0, "name": 1})
        worker_name = w.get("name") if w else None
    # ETA mapping (simple)
    eta_map = {
        "new": "Reviewing your request — we usually respond within 24 hours.",
        "assigned": "Handyman assigned — they'll reach out to schedule.",
        "in_progress": "Job in progress.",
        "completed": "Completed. Hope it went great!",
        "cancelled": "Cancelled.",
    }
    return {
        "job_id": job["job_id"],
        "customer_name": job["customer_name"],
        "service_type": job["service_type"],
        "address": job["address"],
        "status": job["status"],
        "eta_message": eta_map.get(job["status"], ""),
        "quoted_amount": job["quoted_amount"],
        "assigned_worker_name": worker_name,
        "preferred_date": job.get("preferred_date"),
        "preferred_time_slot": job.get("preferred_time_slot"),
        "created_at": job["created_at"],
        "photo_paths": job.get("photo_paths", []),
    }


async def _auto_payout_on_complete(job: dict, admin_user: dict):
    """When a job is marked completed, automatically split the quoted amount:
       15% to marketer (if referral), 50% to worker, remainder to platform.
       Creates payout records and triggers Stripe Transfers when recipients are Connect-enabled.
    """
    amount = float(job.get("quoted_amount") or 0)
    if amount <= 0:
        return []
    worker_id = job.get("assigned_worker_id")
    referral_code = job.get("referral_code")
    marketer_user_id = None
    if referral_code:
        m = await db.users.find_one({"referral_code": referral_code}, {"_id": 0, "user_id": 1})
        if m:
            marketer_user_id = m["user_id"]

    splits = []
    if marketer_user_id:
        splits.append({"user_id": marketer_user_id, "amount": round(amount * 0.15, 2), "type": "referral"})
    if worker_id:
        splits.append({"user_id": worker_id, "amount": round(amount * 0.50, 2), "type": "work"})
    # Platform/admin share (rest) - record as a payout to the founder so the books balance
    paid_sum = sum(s["amount"] for s in splits)
    platform_share = round(amount - paid_sum, 2)
    if platform_share > 0:
        # Pin platform payout to first founding admin (deterministic across restarts)
        founder = None
        for fe in FOUNDING_ADMINS_LIST:
            f = await db.users.find_one({"email": fe}, {"_id": 0, "user_id": 1})
            if f:
                founder = f
                break
        platform_user_id = founder["user_id"] if founder else "platform"
        splits.append({"user_id": platform_user_id, "amount": platform_share, "type": "platform"})

    created = []
    for s in splits:
        stripe_transfer_id = None
        method = "manual"
        # Attempt Stripe Transfer for worker/marketer if they have Connect set up + payouts enabled
        if s["type"] in ("work", "referral") and STRIPE_API_KEY:
            coll, profile = await _get_worker_or_marketer_profile(s["user_id"])
            if profile and profile.get("stripe_account_id") and profile.get("stripe_payouts_enabled"):
                try:
                    transfer = stripe.Transfer.create(
                        amount=int(round(s["amount"] * 100)),
                        currency="usd",
                        destination=profile["stripe_account_id"],
                        transfer_group=job["job_id"],
                        metadata={"job_id": job["job_id"], "type": s["type"], "user_id": s["user_id"]},
                    )
                    stripe_transfer_id = transfer["id"]
                    method = "stripe"
                except stripe.error.StripeError as e:
                    logger.error(f"Auto-payout Stripe Transfer failed for {s['user_id']}: {e}")
        payout = {
            "payout_id": f"pay_{uuid.uuid4().hex[:10]}",
            "user_id": s["user_id"],
            "amount": s["amount"],
            "type": s["type"],
            "job_id": job["job_id"],
            "note": f"Auto-payout on job completion ({int(s['amount']/amount*100)}% of ${amount:.2f})",
            "method": method,
            "stripe_transfer_id": stripe_transfer_id,
            "status": "paid",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.payouts.insert_one(payout)
        payout.pop("_id", None)
        created.append(payout)
    return created


@api.put("/jobs/{job_id}/status")
async def update_job_status(job_id: str, payload: dict, admin: dict = Depends(require_admin)):
    status = payload.get("status")
    if status not in ("new", "assigned", "in_progress", "completed", "cancelled"):
        raise HTTPException(400, "invalid status")

    auto_payouts = []
    if status == "completed" and payload.get("auto_payout", True):
        # Atomic transition: only flip to completed if not already completed (prevents double payout under races)
        job = await db.jobs.find_one_and_update(
            {"job_id": job_id, "status": {"$ne": "completed"}},
            {"$set": {"status": "completed"}},
            projection={"_id": 0},
            return_document=True,  # returns updated doc; if no match -> None
        )
        if job is None:
            # Either job missing or already completed - check which
            existing = await db.jobs.find_one({"job_id": job_id}, {"_id": 0, "status": 1})
            if not existing:
                raise HTTPException(404, "Job not found")
            return {"ok": True, "auto_payouts": [], "note": "already completed"}
        auto_payouts = await _auto_payout_on_complete(job, admin)
    else:
        res = await db.jobs.update_one({"job_id": job_id}, {"$set": {"status": status}})
        if res.matched_count == 0:
            raise HTTPException(404, "Job not found")
    return {"ok": True, "auto_payouts": auto_payouts}


# -------------------- Stripe Connect (Express) --------------------
async def _get_worker_or_marketer_profile(user_id: str):
    """Return the connect profile collection name + record for a user."""
    w = await db.worker_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if w:
        return "worker_profiles", w
    m = await db.marketer_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if m:
        return "marketer_profiles", m
    return None, None


@api.post("/stripe/onboard")
async def stripe_onboard(payload: dict, user: dict = Depends(get_current_user)):
    """Create (or reuse) an Express account for the current user and return a one-time onboarding URL."""
    if not STRIPE_API_KEY:
        raise HTTPException(503, "Stripe not configured")
    origin = payload.get("origin") or "https://nosko.com"
    coll, profile = await _get_worker_or_marketer_profile(user["user_id"])
    if not coll:
        raise HTTPException(400, "Sign up as a worker or marketer first")

    account_id = profile.get("stripe_account_id")
    if not account_id:
        try:
            account = stripe.Account.create(
                type="express",
                country="US",
                email=user.get("email"),
                capabilities={"transfers": {"requested": True}},
                business_type="individual",
                metadata={"user_id": user["user_id"], "role": user.get("role", "")},
            )
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Account.create failed: {e}")
            raise HTTPException(502, f"Stripe error: {str(e)}")
        account_id = account["id"]
        await db[coll].update_one({"user_id": user["user_id"]}, {"$set": {"stripe_account_id": account_id}})

    try:
        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=f"{origin}/account/stripe/refresh",
            return_url=f"{origin}/account/stripe/return",
            type="account_onboarding",
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe AccountLink.create failed: {e}")
        raise HTTPException(502, f"Stripe error: {str(e)}")
    return {"url": link["url"], "stripe_account_id": account_id}


@api.get("/stripe/status")
async def stripe_status(user: dict = Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(503, "Stripe not configured")
    coll, profile = await _get_worker_or_marketer_profile(user["user_id"])
    if not coll or not profile or not profile.get("stripe_account_id"):
        return {"connected": False, "charges_enabled": False, "payouts_enabled": False, "details_submitted": False, "requirements": {}}
    try:
        account = stripe.Account.retrieve(profile["stripe_account_id"])
    except stripe.error.StripeError as e:
        logger.error(f"Stripe Account.retrieve failed: {e}")
        raise HTTPException(502, f"Stripe error: {str(e)}")
    requirements = account.get("requirements") or {}
    status_doc = {
        "stripe_account_id": account["id"],
        "stripe_charges_enabled": bool(account.get("charges_enabled")),
        "stripe_payouts_enabled": bool(account.get("payouts_enabled")),
        "stripe_details_submitted": bool(account.get("details_submitted")),
        "stripe_requirements_currently_due": requirements.get("currently_due", []),
        "stripe_disabled_reason": requirements.get("disabled_reason"),
    }
    await db[coll].update_one({"user_id": user["user_id"]}, {"$set": status_doc})
    return {
        "connected": True,
        "stripe_account_id": account["id"],
        "charges_enabled": status_doc["stripe_charges_enabled"],
        "payouts_enabled": status_doc["stripe_payouts_enabled"],
        "details_submitted": status_doc["stripe_details_submitted"],
        "requirements": {
            "currently_due": status_doc["stripe_requirements_currently_due"],
            "disabled_reason": status_doc["stripe_disabled_reason"],
        },
    }


# -------------------- Payouts / Earnings --------------------
@api.post("/payouts")
async def create_payout(payload: dict, _: dict = Depends(require_admin)):
    target_uid = payload["user_id"]
    amount = float(payload["amount"])
    method = payload.get("method", "manual")
    stripe_transfer_id = None
    error_note = None

    if method == "stripe":
        if not STRIPE_API_KEY:
            raise HTTPException(503, "Stripe not configured")
        coll, profile = await _get_worker_or_marketer_profile(target_uid)
        if not profile or not profile.get("stripe_account_id"):
            raise HTTPException(400, "Recipient has no Stripe Connect account. They need to complete onboarding first.")
        if not profile.get("stripe_payouts_enabled"):
            # Refresh status first to be sure
            try:
                acct = stripe.Account.retrieve(profile["stripe_account_id"])
                if not acct.get("payouts_enabled"):
                    raise HTTPException(400, "Recipient's Stripe account is not yet enabled for payouts.")
                await db[coll].update_one({"user_id": target_uid}, {"$set": {"stripe_payouts_enabled": True}})
            except stripe.error.StripeError as e:
                raise HTTPException(502, f"Stripe error: {str(e)}")
        try:
            transfer = stripe.Transfer.create(
                amount=int(round(amount * 100)),
                currency="usd",
                destination=profile["stripe_account_id"],
                transfer_group=payload.get("job_id") or f"payout_{uuid.uuid4().hex[:8]}",
                metadata={"user_id": target_uid, "type": payload.get("type", "work")},
            )
            stripe_transfer_id = transfer["id"]
        except stripe.error.StripeError as e:
            logger.error(f"Stripe Transfer.create failed: {e}")
            raise HTTPException(502, f"Stripe error: {str(e)}")

    payout = {
        "payout_id": f"pay_{uuid.uuid4().hex[:10]}",
        "user_id": target_uid,
        "amount": amount,
        "type": payload.get("type", "work"),
        "job_id": payload.get("job_id"),
        "note": payload.get("note") or error_note,
        "method": method,
        "stripe_transfer_id": stripe_transfer_id,
        "status": "paid",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.payouts.insert_one(payout)
    payout.pop("_id", None)
    return payout


@api.get("/payouts/me")
async def my_payouts(user: dict = Depends(get_current_user)):
    payouts = await db.payouts.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return payouts


@api.get("/payouts")
async def list_payouts(_: dict = Depends(require_admin)):
    payouts = await db.payouts.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return payouts


@api.get("/earnings/summary")
async def earnings_summary(user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    year_ago = (now - timedelta(days=365)).isoformat()

    async def total(since: Optional[str]) -> float:
        q = {"user_id": user["user_id"], "status": "paid"}
        if since:
            q["created_at"] = {"$gte": since}
        cur = db.payouts.find(q, {"_id": 0, "amount": 1})
        return round(sum([p["amount"] async for p in cur]), 2)

    series = []
    for i in range(11, -1, -1):
        start = (now - timedelta(days=(i + 1) * 7)).isoformat()
        end = (now - timedelta(days=i * 7)).isoformat()
        cur = db.payouts.find(
            {"user_id": user["user_id"], "status": "paid", "created_at": {"$gte": start, "$lt": end}},
            {"_id": 0, "amount": 1},
        )
        s = round(sum([p["amount"] async for p in cur]), 2)
        series.append({"week": f"W-{i}", "amount": s})

    return {
        "weekly": await total(week_ago),
        "monthly": await total(month_ago),
        "yearly": await total(year_ago),
        "all_time": await total(None),
        "series": series,
    }


# -------------------- Portfolio + Site Settings --------------------
@api.get("/portfolio")
async def portfolio_list():
    items = await db.portfolio.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@api.post("/portfolio")
async def portfolio_add(payload: dict, _: dict = Depends(require_admin)):
    item = {
        "photo_id": f"ph_{uuid.uuid4().hex[:10]}",
        "title": payload["title"],
        "description": payload.get("description"),
        "storage_path": payload["storage_path"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.portfolio.insert_one(item)
    item.pop("_id", None)
    return item


@api.delete("/portfolio/{photo_id}")
async def portfolio_delete(photo_id: str, _: dict = Depends(require_admin)):
    res = await db.portfolio.delete_one({"photo_id": photo_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@api.get("/site/settings")
async def get_site_settings():
    s = await db.site_settings.find_one({"key": "default"}, {"_id": 0, "key": 0})
    defaults = SiteSettings().model_dump()
    if not s:
        return defaults
    # Merge stored values over defaults (skip None / empty-string overrides for required scalar copy fields)
    merged = {**defaults}
    for k, v in s.items():
        if v is None:
            continue
        if isinstance(v, str) and not v.strip() and k not in ("services_subheading",):
            continue
        merged[k] = v
    return merged


@api.put("/site/settings")
async def update_site_settings(payload: dict, _: dict = Depends(require_admin)):
    allowed = set(SiteSettings.model_fields.keys())
    update = {k: v for k, v in payload.items() if k in allowed}
    await db.site_settings.update_one({"key": "default"}, {"$set": {"key": "default", **update}}, upsert=True)
    return await get_site_settings()


# -------------------- Admin stats --------------------
@api.get("/admin/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    return {
        "jobs_total": await db.jobs.count_documents({}),
        "jobs_new": await db.jobs.count_documents({"status": "new"}),
        "jobs_completed": await db.jobs.count_documents({"status": "completed"}),
        "workers": await db.worker_profiles.count_documents({}),
        "marketers": await db.marketer_profiles.count_documents({}),
        "users_total": await db.users.count_documents({}),
        "payouts_total": sum(
            [p["amount"] async for p in db.payouts.find({"status": "paid"}, {"_id": 0, "amount": 1})]
        ),
    }


# -------------------- Availability blocking --------------------
@api.get("/availability")
async def get_availability():
    """Public: returns the list of YYYY-MM-DD dates the owner is unavailable."""
    doc = await db.availability.find_one({"key": "default"}, {"_id": 0, "key": 0})
    return {"blocked_dates": (doc or {}).get("blocked_dates", [])}


@api.put("/availability")
async def set_availability(payload: dict, _: dict = Depends(require_admin)):
    """Admin: replace the full set of blocked dates. Accepts {"blocked_dates": ["YYYY-MM-DD", ...]}."""
    dates = payload.get("blocked_dates", [])
    if not isinstance(dates, list):
        raise HTTPException(400, "blocked_dates must be a list")
    cleaned = sorted({str(d).strip() for d in dates if isinstance(d, str) and len(d.strip()) == 10})
    await db.availability.update_one(
        {"key": "default"},
        {"$set": {"key": "default", "blocked_dates": cleaned, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"blocked_dates": cleaned}


# -------------------- App wiring --------------------
@api.get("/")
async def root():
    return {"service": "nosko", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    init_storage()
    try:
        await db.users.create_index("email", unique=True)
        await db.users.create_index("referral_code")
        await db.password_reset_tokens.create_index("token", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
    except Exception as e:
        logger.warning(f"Index creation: {e}")


@app.on_event("shutdown")
async def _shutdown():
    client.close()
