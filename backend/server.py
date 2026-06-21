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
from datetime import datetime, timezone, timedelta, date as date_cls
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
    quote_line = (
        "<p><b>Quote status:</b> <span style=\"background:#FFD600;padding:2px 6px\">PENDING — set price in admin</span></p>"
        if job.get('quoted_amount') in (None, 0)
        else f"<p><b>Quoted:</b> ${job['quoted_amount']:.2f}</p>"
    )
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
        {quote_line}
        {'<p><b>Referral:</b> ' + job['referral_code'] + '</p>' if job.get('referral_code') else ''}
        <p><b>Photos uploaded:</b> {len(job.get('photo_paths', []))}</p>
      </div>
    </div>
    """
    send_email(COMPANY_EMAIL, f"New quote request — {job['customer_name']}", html)


def email_request_received(job: dict, origin: Optional[str] = None):
    """Sent right after a customer submits a request. No price — confirmation only."""
    track_url = f"{origin or 'https://nosko.com'}/track/{job['job_id']}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
      <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
        <h1 style="margin:0;font-size:24px">REQUEST RECEIVED</h1>
      </div>
      <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
        <p>Hey {job['customer_name']},</p>
        <p>We got your request <b>{job['job_id']}</b> for <b>{job['service_type']}</b> at {job['address']}.</p>
        <p>We'll review the photos and details, then email you a custom quote — usually within 24 hours.</p>
        <p style="margin:24px 0"><a href="{track_url}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">TRACK YOUR JOB</a></p>
        <p style="font-size:12px;color:#666">No login needed. Bookmark the link to check status anytime.</p>
        <p>— Nosko Handyman · {COMPANY_EMAIL}</p>
      </div>
    </div>
    """
    send_email(job['customer_email'], "We got your Nosko quote request", html)


def build_quote_email_template(job: dict, amount: float, origin: Optional[str] = None) -> dict:
    """Return default subject + html + text the admin can edit before sending."""
    track_url = f"{origin or 'https://nosko.com'}/track/{job['job_id']}"
    first = (job.get('customer_name') or '').split(' ')[0] or 'there'
    pref = ''
    if job.get('preferred_date'):
        pref = f"<p>Your requested time — <b>{job['preferred_date']} ({job.get('preferred_time_slot') or 'flexible'})</b> — is held for you. Confirm and we'll lock it in.</p>"
    subject = f"Your Nosko quote — Job {job['job_id']}"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
    <h1 style="margin:0;font-size:24px">YOUR QUOTE</h1>
  </div>
  <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
    <p>Hi {first},</p>
    <p>Thanks for sending over your <b>{job.get('service_type','handyman')}</b> request at {job.get('address','')}.</p>
    <p>Here's our quote for the work:</p>
    <div style="background:#0A0A0A;color:#FFD600;padding:18px 24px;margin:18px 0;text-align:center">
      <div style="font-size:12px;letter-spacing:2px">TOTAL QUOTE</div>
      <div style="font-size:42px;font-weight:bold;letter-spacing:-1px">${amount:.2f}</div>
    </div>
    <p>This is a fixed price covering labor. Parts (if any) are itemized separately. $50 visit minimum applies.</p>
    {pref}
    <p>Reply to this email to accept, or click below to view your job status:</p>
    <p style="margin:24px 0"><a href="{track_url}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">VIEW JOB</a></p>
    <p>— Nosson · Nosko Handyman<br>{COMPANY_EMAIL}</p>
  </div>
</div>"""
    text = (
        f"Hi {first},\n\n"
        f"Thanks for sending over your {job.get('service_type','handyman')} request at {job.get('address','')}.\n\n"
        f"Quote: ${amount:.2f}\n\n"
        f"Reply to accept, or view your job: {track_url}\n\n"
        f"— Nosson · Nosko Handyman\n{COMPANY_EMAIL}"
    )
    return {"subject": subject, "html": html, "text": text}


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
    # Newsletter / discount
    newsletter_enabled: bool = True
    newsletter_overline: str = "Email list"
    newsletter_heading: str = "Get 15% off your first job."
    newsletter_subheading: str = "Drop your email — we'll send you a one-time discount code."
    signup_default_percent_off: int = 15

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
    # Reject job if preferred_date is on a blocked day OR a blocked weekday
    pdate = (payload.get("preferred_date") or "").strip() or None
    if pdate:
        avail = await db.availability.find_one({"key": "default"}, {"_id": 0, "blocked_dates": 1, "blocked_weekdays": 1})
        blocked_dates = (avail or {}).get("blocked_dates", [])
        blocked_weekdays = (avail or {}).get("blocked_weekdays", [])
        if pdate in blocked_dates:
            raise HTTPException(400, "Selected date is unavailable. Please pick another day.")
        wlabel = _date_weekday_label(pdate)
        if wlabel and wlabel in blocked_weekdays:
            raise HTTPException(400, "We don't work on that day of the week. Please pick another day.")
    service_type = payload.get("service_type", "General Handyman")
    # Validate promo code if present (but DO NOT mark used yet — only when quote is sent/accepted)
    promo_code = (payload.get("promo_code") or "").strip().upper() or None
    promo_meta = None
    if promo_code:
        dc = await db.discount_codes.find_one({"code": promo_code}, {"_id": 0})
        if not dc or dc.get("used_at"):
            promo_code = None
        else:
            promo_meta = {"code": dc["code"], "percent_off": dc["percent_off"], "code_id": dc["code_id"]}
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
        "preferred_time": payload.get("preferred_time"),  # NEW: "HH:MM" exact
        "preferred_time_slot": payload.get("preferred_time_slot"),  # legacy fallback
        "promo_code": promo_code,
        "promo_meta": promo_meta,
        "quoted_amount": None,
        "quote_status": "pending",   # pending -> sent -> (accepted/declined later)
        "quote_sent_at": None,
        "quote_line_items": [],
        "quote_template_id": None,
        # Scheduling state machine
        "schedule_status": "pending",  # pending | proposed_by_admin | countered_by_customer | agreed | declined
        "proposed_time": None,         # admin's proposed exact "YYYY-MM-DD HH:MM"
        "customer_counter_time": None, # customer's counter "YYYY-MM-DD HH:MM"
        "customer_counter_note": None,
        "scheduled_time": None,        # final agreed time
        "schedule_history": [],        # list of {at, by, action, time?, note?}
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
        email_request_received(job, origin)
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
    quote_status = job.get("quote_status", "sent" if job.get("quoted_amount") not in (None, 0) else "pending")
    # Only expose price after admin explicitly sends the quote email
    public_quote = job.get("quoted_amount") if quote_status == "sent" else None
    return {
        "job_id": job["job_id"],
        "customer_name": job["customer_name"],
        "service_type": job["service_type"],
        "address": job["address"],
        "status": job["status"],
        "eta_message": eta_map.get(job["status"], ""),
        "quoted_amount": public_quote,
        "quote_status": quote_status,
        "quote_sent_at": job.get("quote_sent_at"),
        "assigned_worker_name": worker_name,
        "preferred_date": job.get("preferred_date"),
        "preferred_time": job.get("preferred_time"),
        "preferred_time_slot": job.get("preferred_time_slot"),
        "schedule_status": job.get("schedule_status", "pending"),
        "proposed_time": job.get("proposed_time"),
        "customer_counter_time": job.get("customer_counter_time"),
        "customer_counter_note": job.get("customer_counter_note"),
        "scheduled_time": job.get("scheduled_time"),
        "schedule_history": job.get("schedule_history", []),
        "created_at": job["created_at"],
        "photo_paths": job.get("photo_paths", []),
    }


@api.put("/jobs/{job_id}/quote")
async def save_quote(job_id: str, payload: dict, _: dict = Depends(require_admin)):
    """Admin saves/updates the quote amount (without sending the email)."""
    try:
        amount = float(payload.get("quoted_amount"))
    except (TypeError, ValueError):
        raise HTTPException(400, "quoted_amount (number) required")
    if amount < 0:
        raise HTTPException(400, "Amount must be non-negative")
    res = await db.jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "quoted_amount": round(amount, 2),
            "quote_status": "draft",
        }},
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Job not found")
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    return job


@api.post("/jobs/{job_id}/quote-preview")
async def preview_quote_email(job_id: str, payload: dict, request: Request, _: dict = Depends(require_admin)):
    """Return a pre-filled subject + HTML the admin can edit before sending.

    Body: { quoted_amount, template_id? (uses default if missing), line_items?: [{label, amount}] }
    """
    try:
        amount = float(payload.get("quoted_amount"))
    except (TypeError, ValueError):
        raise HTTPException(400, "quoted_amount (number) required")
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    origin = payload.get("origin") or request.headers.get("origin") or str(request.base_url).rstrip("/")
    line_items = payload.get("line_items") or []
    # Pick template
    tpl = None
    template_id = payload.get("template_id")
    if template_id:
        tpl = await db.email_templates.find_one({"template_id": template_id}, {"_id": 0})
    if not tpl:
        tpl = await db.email_templates.find_one({"is_default": True}, {"_id": 0})
    discount = job.get("promo_meta") or None
    if tpl:
        v = _template_vars_for_job(job, amount, origin, line_items, discount)
        subject = _render_template(tpl["subject_template"], v)
        html = _render_template(tpl["html_template"], v)
        text = (
            f"Hi {v['first_name']},\n\nYour Nosko quote for {v['service_type']} at {v['address']}: "
            f"${v['amount']}\n\nView job: {v['track_url']}\n\n— Nosko Handyman"
        )
        return {"subject": subject, "html": html, "text": text, "template_id": tpl["template_id"], "template_name": tpl["name"]}
    # Fallback hardcoded template (shouldn't happen after seed)
    return build_quote_email_template(job, amount, origin)


@api.post("/jobs/{job_id}/send-quote")
async def send_quote(job_id: str, payload: dict, request: Request, _: dict = Depends(require_admin)):
    """Send the customer the quote email (admin can override subject/html/text + supply line items + template)."""
    try:
        amount = float(payload.get("quoted_amount"))
    except (TypeError, ValueError):
        raise HTTPException(400, "quoted_amount (number) required")
    if amount < 0:
        raise HTTPException(400, "Amount must be non-negative")
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")

    origin = payload.get("origin") or request.headers.get("origin") or str(request.base_url).rstrip("/")
    line_items = payload.get("line_items") or []
    template_id = payload.get("template_id")

    # Build defaults from template if subject/html not provided
    tpl = None
    if template_id:
        tpl = await db.email_templates.find_one({"template_id": template_id}, {"_id": 0})
    if not tpl:
        tpl = await db.email_templates.find_one({"is_default": True}, {"_id": 0})
    discount = job.get("promo_meta") or None
    if tpl:
        v = _template_vars_for_job(job, amount, origin, line_items, discount)
        default_subject = _render_template(tpl["subject_template"], v)
        default_html = _render_template(tpl["html_template"], v)
    else:
        legacy = build_quote_email_template(job, amount, origin)
        default_subject, default_html = legacy["subject"], legacy["html"]

    subject = (payload.get("subject") or default_subject).strip()
    html = payload.get("html") or default_html
    text = payload.get("text") or ""

    sent_ok = send_email(job["customer_email"], subject, html, text or None)
    if not sent_ok:
        raise HTTPException(502, "Email send failed — check SMTP credentials.")

    now = datetime.now(timezone.utc).isoformat()
    # Schedule: admin proposes a time alongside the quote. Defaults to customer's preferred if not supplied.
    proposed_time = (payload.get("proposed_time") or "").strip() or None
    if not proposed_time:
        cd = job.get("preferred_date")
        ct = job.get("preferred_time")
        if cd and ct:
            proposed_time = f"{cd} {ct}"
    history = job.get("schedule_history", []) or []
    history.append({
        "at": now, "by": "admin", "action": "proposed",
        "time": proposed_time, "note": payload.get("schedule_note") or None,
    })
    set_doc = {
        "quoted_amount": round(amount, 2),
        "quote_status": "sent",
        "quote_sent_at": now,
        "last_quote_subject": subject,
        "last_quote_html": html,
        "quote_line_items": line_items,
        "quote_template_id": template_id,
        "schedule_status": "proposed_by_admin",
        "proposed_time": proposed_time,
        "schedule_history": history,
    }
    await db.jobs.update_one({"job_id": job_id}, {"$set": set_doc})

    # Mark promo code as used (single-use) now that the quote has been delivered
    if job.get("promo_meta") and job["promo_meta"].get("code_id"):
        await db.discount_codes.update_one(
            {"code_id": job["promo_meta"]["code_id"], "used_at": None},
            {"$set": {"used_at": now, "used_on_job_id": job_id}},
        )
    return {"ok": True, "quote_sent_at": now, "to": job["customer_email"], "proposed_time": proposed_time}


# -------------------- Scheduling: Accept / Decline / Counter --------------------
def _fmt_dt_human(s: Optional[str]) -> str:
    if not s:
        return "TBD"
    return s.replace("T", " ")[:16]


def _email_schedule_to_admin(job: dict, action: str, time_str: Optional[str], note: Optional[str]):
    """Email Nosson when customer accepts/declines/counters the quote."""
    color = {"accepted": "#16A34A", "declined": "#DC2626", "countered": "#F59E0B"}.get(action, "#0A0A0A")
    label = {"accepted": "ACCEPTED", "declined": "DECLINED", "countered": "COUNTERED"}.get(action, action.upper())
    extra = ""
    if action == "countered" and time_str:
        extra = f"<p><b>Customer wants:</b> {_fmt_dt_human(time_str)}</p>"
    if note:
        extra += f"<p><b>Note:</b> {note}</p>"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="background:{color};color:white;padding:18px 24px">
    <h1 style="margin:0;font-size:22px">{label} — {job.get('customer_name','Customer')}</h1>
  </div>
  <div style="padding:18px 24px;border:2px solid {color};border-top:0">
    <p>Job <b>{job['job_id']}</b> · {job.get('service_type','')}</p>
    <p><b>Quoted:</b> ${(job.get('quoted_amount') or 0):.2f}</p>
    <p><b>Your proposed time:</b> {_fmt_dt_human(job.get('proposed_time'))}</p>
    {extra}
    <p>Open the admin dashboard to respond.</p>
  </div>
</div>"""
    send_email(COMPANY_EMAIL, f"Job {job['job_id']} — quote {label.lower()}", html)


def _email_schedule_to_customer(job: dict, action: str, time_str: Optional[str], note: Optional[str], origin: Optional[str] = None):
    """Email the customer when admin agrees / counters / declines."""
    track_url = f"{origin or 'https://nosko.com'}/track/{job['job_id']}"
    color = {"agreed": "#16A34A", "declined": "#DC2626", "counter": "#F59E0B"}.get(action, "#0A0A0A")
    if action == "agreed":
        title, body = "BOOKING CONFIRMED", f"<p>You're locked in for <b>{_fmt_dt_human(time_str)}</b>.</p>"
    elif action == "declined":
        title, body = "WE CAN'T MAKE THAT WORK", "<p>Sorry — that time/scope isn't workable on our end. Reply if you'd like to find another option.</p>"
    else:
        title, body = "NEW TIME PROPOSAL", f"<p>Nosson can do <b>{_fmt_dt_human(time_str)}</b> instead. Open the link below to accept, decline, or counter.</p>"
    if note:
        body += f"<p style='background:#FFF7CD;padding:8px 12px;border-left:3px solid #F59E0B'>Note from Nosson: {note}</p>"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="background:{color};color:white;padding:18px 24px;border:2px solid #0A0A0A">
    <h1 style="margin:0;font-size:22px">{title}</h1>
  </div>
  <div style="padding:18px 24px;border:2px solid #0A0A0A;border-top:0">
    <p>Hi {(job.get('customer_name') or '').split(' ')[0] or 'there'},</p>
    {body}
    <p style="margin:20px 0"><a href="{track_url}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">VIEW JOB</a></p>
    <p>— Nosko Handyman</p>
  </div>
</div>"""
    subject_map = {"agreed": "Booking confirmed", "declined": "About your Nosko quote", "counter": "New time proposal"}
    send_email(job["customer_email"], subject_map.get(action, "Update on your job"), html)


@api.post("/jobs/track/{job_id}/respond")
async def customer_respond(job_id: str, payload: dict, request: Request):
    """Anonymous public endpoint — customer accepts / declines / counters from the track page."""
    action = (payload.get("action") or "").strip().lower()
    if action not in ("accept", "decline", "counter"):
        raise HTTPException(400, "action must be accept|decline|counter")
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")
    # Only allow response if quote has been sent and the back-and-forth isn't already settled.
    if job.get("schedule_status") in (None, "pending"):
        raise HTTPException(400, "Quote has not been sent yet")
    if job.get("schedule_status") in ("agreed", "declined"):
        raise HTTPException(400, "This booking is already settled")

    now = datetime.now(timezone.utc).isoformat()
    history = job.get("schedule_history", []) or []
    note = (payload.get("note") or "").strip() or None
    set_doc = {"schedule_history": history}

    if action == "accept":
        agreed_time = job.get("proposed_time")
        set_doc.update({
            "schedule_status": "agreed",
            "scheduled_time": agreed_time,
            "customer_counter_time": None,
            "customer_counter_note": note,
        })
        history.append({"at": now, "by": "customer", "action": "accepted", "time": agreed_time, "note": note})
    elif action == "decline":
        set_doc.update({"schedule_status": "declined", "customer_counter_note": note})
        history.append({"at": now, "by": "customer", "action": "declined", "note": note})
    else:  # counter
        ct = (payload.get("counter_time") or "").strip()
        if not ct:
            raise HTTPException(400, "counter_time (YYYY-MM-DD HH:MM) required")
        set_doc.update({
            "schedule_status": "countered_by_customer",
            "customer_counter_time": ct,
            "customer_counter_note": note,
        })
        history.append({"at": now, "by": "customer", "action": "countered", "time": ct, "note": note})

    await db.jobs.update_one({"job_id": job_id}, {"$set": set_doc})
    updated = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    try:
        _email_schedule_to_admin(updated, action + "ed" if action != "counter" else "countered", set_doc.get("customer_counter_time"), note)
    except Exception as e:
        logger.error(f"Schedule-to-admin email failed: {e}")
    return {"ok": True, "schedule_status": set_doc["schedule_status"], "scheduled_time": set_doc.get("scheduled_time")}


@api.post("/jobs/{job_id}/respond-counter")
async def admin_respond_counter(job_id: str, payload: dict, request: Request, _: dict = Depends(require_admin)):
    """Admin reacts to customer counter: agree | counter (with new time) | decline."""
    action = (payload.get("action") or "").strip().lower()
    if action not in ("agree", "counter", "decline"):
        raise HTTPException(400, "action must be agree|counter|decline")
    job = await db.jobs.find_one({"job_id": job_id}, {"_id": 0})
    if not job:
        raise HTTPException(404, "Job not found")

    now = datetime.now(timezone.utc).isoformat()
    history = job.get("schedule_history", []) or []
    note = (payload.get("note") or "").strip() or None
    origin = payload.get("origin") or request.headers.get("origin") or str(request.base_url).rstrip("/")

    if action == "agree":
        agreed = job.get("customer_counter_time") or job.get("proposed_time")
        if not agreed:
            raise HTTPException(400, "No customer counter time to agree to")
        set_doc = {"schedule_status": "agreed", "scheduled_time": agreed}
        history.append({"at": now, "by": "admin", "action": "agreed", "time": agreed, "note": note})
        await db.jobs.update_one({"job_id": job_id}, {"$set": {**set_doc, "schedule_history": history}})
        try:
            _email_schedule_to_customer(job, "agreed", agreed, note, origin)
        except Exception as e:
            logger.error(f"Customer agree email failed: {e}")
        return {"ok": True, "scheduled_time": agreed, "schedule_status": "agreed"}

    if action == "decline":
        history.append({"at": now, "by": "admin", "action": "declined", "note": note})
        await db.jobs.update_one({"job_id": job_id}, {"$set": {"schedule_status": "declined", "schedule_history": history}})
        try:
            _email_schedule_to_customer(job, "declined", None, note, origin)
        except Exception as e:
            logger.error(f"Customer decline email failed: {e}")
        return {"ok": True, "schedule_status": "declined"}

    # counter
    new_time = (payload.get("proposed_time") or "").strip()
    if not new_time:
        raise HTTPException(400, "proposed_time (YYYY-MM-DD HH:MM) required")
    history.append({"at": now, "by": "admin", "action": "countered", "time": new_time, "note": note})
    await db.jobs.update_one({"job_id": job_id}, {"$set": {
        "schedule_status": "proposed_by_admin",
        "proposed_time": new_time,
        "customer_counter_time": None,
        "customer_counter_note": None,
        "schedule_history": history,
    }})
    try:
        _email_schedule_to_customer(job, "counter", new_time, note, origin)
    except Exception as e:
        logger.error(f"Customer counter email failed: {e}")
    return {"ok": True, "proposed_time": new_time, "schedule_status": "proposed_by_admin"}




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


# -------------------- Newsletter, discount codes, email templates, blasts --------------------
import random
import string as _string


def _new_code(prefix: str = "NOSKO") -> str:
    suffix = "".join(random.choices(_string.ascii_uppercase + _string.digits, k=6))
    return f"{prefix}{suffix}"


async def _generate_unique_code(prefix: str = "NOSKO") -> str:
    for _ in range(8):
        c = _new_code(prefix)
        if not await db.discount_codes.find_one({"code": c}):
            return c
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def _email_signup_template(code: str, percent_off: int, contact_email: str, domain: str) -> dict:
    subject = f"Your {percent_off}% off code is {code}"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
    <h1 style="margin:0;font-size:22px">WELCOME TO NOSKO</h1>
  </div>
  <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
    <p>Thanks for joining the list. Here's your one-time discount code:</p>
    <div style="background:#0A0A0A;color:#FFD600;padding:18px 24px;margin:18px 0;text-align:center">
      <div style="font-size:12px;letter-spacing:2px">{percent_off}% OFF YOUR FIRST QUOTE</div>
      <div style="font-size:30px;font-weight:bold;letter-spacing:1px;margin-top:6px">{code}</div>
    </div>
    <p>Just paste it in the Promo code field when you request a quote at <a href="https://{domain}">{domain}</a>.</p>
    <p style="font-size:12px;color:#666">One-time use. One code per email. Expires when you use it.</p>
    <p>— Nosko Handyman · {contact_email}</p>
  </div>
</div>"""
    text = (
        f"Welcome to Nosko!\n\nYour {percent_off}% off code: {code}\n\n"
        f"Use it in the Promo code field at https://{domain}/request\n"
        f"One-time use, one per email.\n\n— Nosko Handyman"
    )
    return {"subject": subject, "html": html, "text": text}


async def _get_setting(key: str, default):
    s = await db.site_settings.find_one({"key": "default"}, {"_id": 0})
    if not s:
        return default
    v = s.get(key)
    return default if v in (None, "") else v


@api.post("/subscribers")
async def subscribe(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(400, "Valid email required")
    existing = await db.subscribers.find_one({"email": email}, {"_id": 0})
    if existing:
        code_doc = await db.discount_codes.find_one({"code_id": existing.get("discount_code_id")}, {"_id": 0})
        if code_doc and not code_doc.get("used_at"):
            domain = await _get_setting("website_domain", "noskotx.com")
            contact = await _get_setting("contact_email", COMPANY_EMAIL)
            tmpl = _email_signup_template(code_doc["code"], code_doc["percent_off"], contact, domain)
            try:
                send_email(email, tmpl["subject"], tmpl["html"], tmpl["text"])
            except Exception:
                pass
            return {"already_subscribed": True, "code": code_doc["code"], "percent_off": code_doc["percent_off"]}
        return {"already_subscribed": True, "code": None, "message": "Welcome back — your previous code was already used."}

    percent_off = int(await _get_setting("signup_default_percent_off", 15))
    code = await _generate_unique_code("NOSKO")
    code_id = f"dc_{uuid.uuid4().hex[:10]}"
    now = datetime.now(timezone.utc).isoformat()
    await db.discount_codes.insert_one({
        "code_id": code_id, "code": code, "percent_off": percent_off, "email": email,
        "issued_at": now, "used_at": None, "used_on_job_id": None,
        "created_by": "auto_signup", "notes": "",
    })
    await db.subscribers.insert_one({
        "sub_id": f"sub_{uuid.uuid4().hex[:10]}",
        "email": email, "subscribed_at": now,
        "source": payload.get("source") or "landing_footer",
        "discount_code_id": code_id,
    })

    domain = await _get_setting("website_domain", "noskotx.com")
    contact = await _get_setting("contact_email", COMPANY_EMAIL)
    tmpl = _email_signup_template(code, percent_off, contact, domain)
    sent = False
    try:
        sent = send_email(email, tmpl["subject"], tmpl["html"], tmpl["text"])
    except Exception as e:
        logger.error(f"Signup email failed for {email}: {e}")
    return {"ok": True, "code": code, "percent_off": percent_off, "email_sent": sent}


@api.get("/subscribers")
async def list_subscribers(_: dict = Depends(require_admin)):
    subs = [s async for s in db.subscribers.find({}, {"_id": 0}).sort("subscribed_at", -1)]
    code_ids = [s["discount_code_id"] for s in subs if s.get("discount_code_id")]
    codes_by_id = {}
    if code_ids:
        async for c in db.discount_codes.find({"code_id": {"$in": code_ids}}, {"_id": 0}):
            codes_by_id[c["code_id"]] = c
    for s in subs:
        c = codes_by_id.get(s.get("discount_code_id")) or {}
        s["code"] = c.get("code")
        s["percent_off"] = c.get("percent_off")
        s["code_used"] = bool(c.get("used_at"))
        s["code_used_on_job_id"] = c.get("used_on_job_id")
    return subs


@api.delete("/subscribers/{sub_id}")
async def delete_subscriber(sub_id: str, _: dict = Depends(require_admin)):
    res = await db.subscribers.delete_one({"sub_id": sub_id})
    return {"deleted": res.deleted_count}


@api.get("/discount-codes")
async def list_discount_codes(_: dict = Depends(require_admin)):
    return [c async for c in db.discount_codes.find({}, {"_id": 0}).sort("issued_at", -1)]


@api.post("/discount-codes")
async def create_discount_code(payload: dict, _: dict = Depends(require_admin)):
    try:
        percent_off = int(payload.get("percent_off"))
    except (TypeError, ValueError):
        raise HTTPException(400, "percent_off (integer 1-100) required")
    if percent_off < 1 or percent_off > 100:
        raise HTTPException(400, "percent_off must be 1-100")
    code = (payload.get("code") or "").strip().upper() or await _generate_unique_code("NOSKO")
    if await db.discount_codes.find_one({"code": code}):
        raise HTTPException(409, "Code already exists")
    doc = {
        "code_id": f"dc_{uuid.uuid4().hex[:10]}",
        "code": code, "percent_off": percent_off,
        "email": (payload.get("email") or "").strip().lower() or None,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "used_at": None, "used_on_job_id": None,
        "created_by": "admin_manual",
        "notes": payload.get("notes") or "",
    }
    await db.discount_codes.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/discount-codes/{code_id}")
async def update_discount_code(code_id: str, payload: dict, _: dict = Depends(require_admin)):
    update = {}
    if "percent_off" in payload:
        try:
            p = int(payload["percent_off"])
            if 1 <= p <= 100:
                update["percent_off"] = p
        except (TypeError, ValueError):
            raise HTTPException(400, "percent_off must be 1-100")
    if "code" in payload:
        new_code = (payload["code"] or "").strip().upper()
        if new_code:
            existing = await db.discount_codes.find_one({"code": new_code, "code_id": {"$ne": code_id}})
            if existing:
                raise HTTPException(409, "Another code already uses that string")
            update["code"] = new_code
    if "notes" in payload:
        update["notes"] = payload["notes"] or ""
    if payload.get("reset_usage"):
        update["used_at"] = None
        update["used_on_job_id"] = None
    if not update:
        raise HTTPException(400, "No editable fields supplied")
    res = await db.discount_codes.update_one({"code_id": code_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Code not found")
    return await db.discount_codes.find_one({"code_id": code_id}, {"_id": 0})


@api.delete("/discount-codes/{code_id}")
async def delete_discount_code(code_id: str, _: dict = Depends(require_admin)):
    res = await db.discount_codes.delete_one({"code_id": code_id})
    return {"deleted": res.deleted_count}


@api.post("/discount-codes/validate")
async def validate_discount_code(payload: dict):
    code = (payload.get("code") or "").strip().upper()
    if not code:
        return {"valid": False, "error": "Enter a code"}
    doc = await db.discount_codes.find_one({"code": code}, {"_id": 0})
    if not doc:
        return {"valid": False, "error": "Code not found"}
    if doc.get("used_at"):
        return {"valid": False, "error": "This code has already been used"}
    return {"valid": True, "percent_off": doc["percent_off"], "code": code}


DEFAULT_TEMPLATES = [
    {
        "name": "Friendly quote",
        "subject_template": "Your Nosko quote — Job {{job_id}}",
        "html_template": """<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="background:#FFD600;padding:18px 24px;border:2px solid #0A0A0A">
    <h1 style="margin:0;font-size:24px">YOUR QUOTE</h1>
  </div>
  <div style="padding:24px;border:2px solid #0A0A0A;border-top:0">
    <p>Hey {{first_name}},</p>
    <p>Thanks for the photo of your {{service_type}} at {{address}}. Here's what I'm thinking:</p>
    {{breakdown_block}}
    <div style="background:#0A0A0A;color:#FFD600;padding:18px 24px;margin:18px 0;text-align:center">
      <div style="font-size:12px;letter-spacing:2px">TOTAL</div>
      <div style="font-size:42px;font-weight:bold;letter-spacing:-1px">${{amount}}</div>
    </div>
    <p>Reply to lock in your {{preferred_date}} slot, or hit the button:</p>
    <p style="margin:24px 0"><a href="{{track_url}}" style="background:#0A0A0A;color:#FFD600;padding:12px 20px;text-decoration:none;border:2px solid #0A0A0A;display:inline-block">VIEW JOB</a></p>
    <p>— Nosson · Nosko Handyman<br>{{contact_email}}</p>
  </div>
</div>""",
        "is_default": True,
    },
    {
        "name": "Formal",
        "subject_template": "Quote for {{service_type}} — Job {{job_id}}",
        "html_template": """<div style="font-family:Georgia,serif;max-width:560px;margin:0 auto;color:#0A0A0A">
  <div style="border-bottom:3px solid #0A0A0A;padding-bottom:12px">
    <h2 style="margin:0">Nosko Handyman — Quote</h2>
    <div style="font-size:12px;color:#666">{{contact_email}}</div>
  </div>
  <div style="padding:18px 0">
    <p>Dear {{customer_name}},</p>
    <p>Thank you for considering Nosko Handyman for your {{service_type}} project at {{address}}. Please find our quote below:</p>
    {{breakdown_block}}
    <table style="width:100%;border-collapse:collapse;margin:18px 0">
      <tr><td style="padding:8px;border-top:2px solid #000;font-weight:bold">Total</td><td style="padding:8px;border-top:2px solid #000;text-align:right;font-weight:bold">${{amount}}</td></tr>
    </table>
    <p>Should you wish to proceed, kindly reply to this email or use the link below to confirm.</p>
    <p><a href="{{track_url}}">View job status →</a></p>
    <p>Regards,<br>Nosson Kosowsky<br>Nosko Handyman</p>
  </div>
</div>""",
        "is_default": False,
    },
    {
        "name": "Quick price",
        "subject_template": "${{amount}} for your {{service_type}}",
        "html_template": """<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto">
  <p>Hi {{first_name}},</p>
  <p>Quick price for {{service_type}} at {{address}}:</p>
  <div style="background:#FFD600;padding:24px;text-align:center;border:2px solid #000;margin:14px 0">
    <div style="font-size:48px;font-weight:bold;letter-spacing:-2px">${{amount}}</div>
  </div>
  {{breakdown_block}}
  <p>Reply yes to book — <a href="{{track_url}}">track here</a>.</p>
  <p>— Nosson</p>
</div>""",
        "is_default": False,
    },
]


async def _seed_default_templates():
    if await db.email_templates.count_documents({}) == 0:
        for t in DEFAULT_TEMPLATES:
            await db.email_templates.insert_one({
                "template_id": f"tpl_{uuid.uuid4().hex[:10]}",
                "name": t["name"],
                "subject_template": t["subject_template"],
                "html_template": t["html_template"],
                "is_default": t["is_default"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })


def _render_template(tpl_str: str, vars_: dict) -> str:
    out = tpl_str
    for k, v in vars_.items():
        out = out.replace("{{" + k + "}}", str(v if v is not None else ""))
    return out


def _build_breakdown_block(line_items: list) -> str:
    if not line_items:
        return ""
    rows = "".join(
        f"<tr><td style='padding:6px 0;border-bottom:1px dashed #ccc'>{li.get('label','')}</td>"
        f"<td style='padding:6px 0;border-bottom:1px dashed #ccc;text-align:right'>${float(li.get('amount',0)):.2f}</td></tr>"
        for li in line_items
    )
    return (
        "<table style='width:100%;border-collapse:collapse;margin:8px 0;font-size:14px'>"
        + rows + "</table>"
    )


def _template_vars_for_job(job: dict, amount: float, origin: Optional[str], line_items: list, discount: Optional[dict]) -> dict:
    track_url = f"{origin or 'https://nosko.com'}/track/{job['job_id']}"
    first = (job.get("customer_name") or "").split(" ")[0] or "there"
    breakdown_html = _build_breakdown_block(line_items)
    if discount:
        breakdown_html += (
            f"<div style='background:#FFD600;border:2px solid #000;padding:10px 14px;margin:8px 0;font-size:14px'>"
            f"Promo applied · <b>{discount.get('code','')}</b> · {discount.get('percent_off',0)}% off</div>"
        )
    # Proposed time line
    pt = job.get("proposed_time")
    if not pt:
        cd, ct = job.get("preferred_date"), job.get("preferred_time")
        if cd and ct:
            pt = f"{cd} {ct}"
    pt_label = pt or job.get("preferred_date") or "your preferred"
    return {
        "job_id": job["job_id"],
        "customer_name": job.get("customer_name", ""),
        "first_name": first,
        "service_type": job.get("service_type", "handyman"),
        "address": job.get("address", ""),
        "amount": f"{amount:.2f}",
        "preferred_date": pt_label,
        "proposed_time": pt or "",
        "track_url": track_url,
        "contact_email": COMPANY_EMAIL,
        "breakdown_block": breakdown_html,
    }


@api.get("/email-templates")
async def list_email_templates(_: dict = Depends(require_admin)):
    return [t async for t in db.email_templates.find({}, {"_id": 0}).sort("created_at", 1)]


@api.post("/email-templates")
async def create_email_template(payload: dict, _: dict = Depends(require_admin)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "name required")
    doc = {
        "template_id": f"tpl_{uuid.uuid4().hex[:10]}",
        "name": name,
        "subject_template": payload.get("subject_template") or "Your Nosko quote",
        "html_template": payload.get("html_template") or "",
        "is_default": bool(payload.get("is_default", False)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if doc["is_default"]:
        await db.email_templates.update_many({}, {"$set": {"is_default": False}})
    await db.email_templates.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api.put("/email-templates/{template_id}")
async def update_email_template(template_id: str, payload: dict, _: dict = Depends(require_admin)):
    update = {k: payload[k] for k in ("name", "subject_template", "html_template") if k in payload}
    if "is_default" in payload:
        update["is_default"] = bool(payload["is_default"])
        if update["is_default"]:
            await db.email_templates.update_many({}, {"$set": {"is_default": False}})
    if not update:
        raise HTTPException(400, "Nothing to update")
    res = await db.email_templates.update_one({"template_id": template_id}, {"$set": update})
    if res.matched_count == 0:
        raise HTTPException(404, "Template not found")
    return await db.email_templates.find_one({"template_id": template_id}, {"_id": 0})


@api.delete("/email-templates/{template_id}")
async def delete_email_template(template_id: str, _: dict = Depends(require_admin)):
    res = await db.email_templates.delete_one({"template_id": template_id})
    return {"deleted": res.deleted_count}


@api.post("/email-blasts/preview")
async def preview_blast(payload: dict, _: dict = Depends(require_admin)):
    subject = (payload.get("subject") or "").strip()
    html = payload.get("html") or ""
    if not subject:
        raise HTTPException(400, "Subject required")
    count = await db.subscribers.count_documents({})
    return {"subject": subject, "html": html, "recipient_count": count}


@api.post("/email-blasts")
async def send_blast(payload: dict, _: dict = Depends(require_admin)):
    subject = (payload.get("subject") or "").strip()
    html = payload.get("html") or ""
    text = payload.get("text") or ""
    if not subject or not html:
        raise HTTPException(400, "Subject and body required")
    recipients = [s["email"] async for s in db.subscribers.find({}, {"_id": 0, "email": 1})]
    sent_count = 0
    failed = []
    for email in recipients:
        try:
            ok = send_email(email, subject, html, text or None)
            if ok:
                sent_count += 1
            else:
                failed.append(email)
        except Exception as e:
            logger.error(f"Blast to {email} failed: {e}")
            failed.append(email)
    blast = {
        "blast_id": f"blast_{uuid.uuid4().hex[:10]}",
        "subject": subject, "html": html, "text": text,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "recipient_count": len(recipients),
        "sent_count": sent_count, "failed_count": len(failed),
    }
    await db.email_blasts.insert_one(blast)
    blast.pop("_id", None)
    return blast


@api.get("/email-blasts")
async def list_blasts(_: dict = Depends(require_admin)):
    return [b async for b in db.email_blasts.find({}, {"_id": 0}).sort("sent_at", -1).limit(50)]




# -------------------- Availability blocking --------------------
WEEKDAY_LABELS_PY = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]  # Python weekday() order


def _date_weekday_label(d: str) -> Optional[str]:
    try:
        y, m, day = (int(x) for x in d.split("-"))
        return WEEKDAY_LABELS_PY[date_cls(y, m, day).weekday()]
    except Exception:
        return None


@api.get("/availability")
async def get_availability():
    """Public: returns blocked specific dates AND blocked weekdays."""
    doc = await db.availability.find_one({"key": "default"}, {"_id": 0, "key": 0})
    return {
        "blocked_dates": (doc or {}).get("blocked_dates", []),
        "blocked_weekdays": (doc or {}).get("blocked_weekdays", []),
    }


@api.put("/availability")
async def set_availability(payload: dict, _: dict = Depends(require_admin)):
    """Admin: replace blocked_dates and/or blocked_weekdays."""
    update = {"updated_at": datetime.now(timezone.utc).isoformat(), "key": "default"}
    if "blocked_dates" in payload:
        dates = payload.get("blocked_dates") or []
        if not isinstance(dates, list):
            raise HTTPException(400, "blocked_dates must be a list")
        update["blocked_dates"] = sorted({str(d).strip() for d in dates if isinstance(d, str) and len(d.strip()) == 10})
    if "blocked_weekdays" in payload:
        wdays = payload.get("blocked_weekdays") or []
        if not isinstance(wdays, list):
            raise HTTPException(400, "blocked_weekdays must be a list")
        allowed = {"sun", "mon", "tue", "wed", "thu", "fri", "sat"}
        update["blocked_weekdays"] = sorted({str(w).lower().strip() for w in wdays if isinstance(w, str) and str(w).lower().strip() in allowed})
    await db.availability.update_one({"key": "default"}, {"$set": update}, upsert=True)
    return await get_availability()


# -------------------- App wiring --------------------
@api.get("/")
async def root():
    return {"service": "nosko", "status": "ok"}


app.include_router(api)

# CORS: when origins includes "*", use regex so credentialed requests work for any origin
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
if "*" in _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=_cors_origins,
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
        await db.subscribers.create_index("email", unique=True)
        await db.discount_codes.create_index("code", unique=True)
        await db.discount_codes.create_index("code_id", unique=True)
        await _seed_default_templates()
    except Exception as e:
        logger.warning(f"Index creation: {e}")


@app.on_event("shutdown")
async def _shutdown():
    client.close()
