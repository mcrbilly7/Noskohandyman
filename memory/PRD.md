# Nosko Handyman — PRD

## Original problem statement
Build a website for "Nosko" handyman company. Set prices ($25 switch/outlet, $50 minimum). W9 worker + marketer signup with 15% referral profit share. Admin paying workers, earnings dashboards (weekly/monthly/yearly), portfolio + admin site editor, job request with photo upload, automated emails.

## Iteration 2 user requirements (Feb 2026)
- Make site cleaner and more professional ✓
- Confirm: handyman does everything (outlet is only known price) ✓
- **Minimum is $50 per visit** (was $25) ✓
- Founding admins: **noskotx@gmail.com**, **nossonkosowsky32@gmail.com** ✓
- Founding admins can change other accounts to admin/developer/worker/marketer/customer ✓
- Forgot password + reset flow ✓ (for email/password users)
- Automated emails on signup and quote request ✓ (Gmail SMTP)
- noskotx@gmail.com is company email ✓
- DFW Metroplex business ✓
- **Full account settings page for every account** ✓

## Tech stack
- Backend: FastAPI + motor (async MongoDB) + bcrypt + smtplib + Emergent Object Storage
- Frontend: React 19 + Tailwind + shadcn/ui + Recharts + Sonner toasts
- Auth: hybrid — Emergent Google OAuth + email/password (bcrypt + session_token cookie)

## Implemented endpoints (iter 2)
- **Email/password auth**: `/api/auth/register`, `/api/auth/login`, `/api/auth/forgot-password`, `/api/auth/reset-password`
- **Google OAuth**: `/api/auth/session` (Emergent OAuth exchange)
- **Account**: `PUT /api/users/me` (name/phone/location/notify_email/password)
- **Team management**: `GET /api/admin/users`, `PUT /api/admin/users/{id}/role` (founder-only)
- All prior endpoints (jobs, workers, marketers, w9, payouts, portfolio, site settings) retained

## Implemented pages (iter 2)
- Cleaner LandingPage (removed heavy yellow blocks, added services grid, DFW callout, free-quote panel)
- `/login`, `/register`, `/forgot-password`, `/reset-password`
- `/account` — full account settings (any user can edit profile + password)
- AdminDashboard: new **Team** tab — founders see role dropdown per user, non-founders see read-only list

## Email notifications (Gmail SMTP)
- Welcome email on signup
- New-job-request → noskotx@gmail.com (company)
- New-job-request confirmation → customer
- Password reset link → user

⚠️ **SMTP password issue**: Gmail rejects normal passwords. The provided password "Bigbilly101!" gets a 535 BadCredentials from Google. Backend handles this gracefully (no 500s) but no emails actually deliver yet. **Owner must**: enable 2-Step Verification on noskotx@gmail.com → generate App Password at https://myaccount.google.com/apppasswords → replace `SMTP_PASSWORD` in `/app/backend/.env` with the 16-char app password.

## Pricing logic
- Every visit has a **$50 minimum**. Quotes < $50 are clamped to $50 server-side.
- Switch/outlet swap is **$25 per swap**. A single-outlet job still totals $50 (minimum). 2-outlet job = $50 (2×$25). 3-outlet job = $75. Etc. Copy updated to reflect this clearly.

## Tests
- **66/66 backend tests pass** (iter1 + iter2). See `/app/test_reports/iteration_2.json`.

## Backlog (P0 → P2)
- **P0 (owner action)**: Replace Gmail SMTP password with a real Google App Password.
- **P1**: Real Stripe Connect Express onboarding (currently admin records payouts manually with method='stripe').
- **P1**: Pydantic request models on POST endpoints for 422 instead of 500 on missing fields.
- **P1**: Move SMTP sends to FastAPI BackgroundTasks (currently synchronous in async handlers — adds latency under failure).
- **P2**: Job-status emails to customer + worker.
- **P2**: TTL index on user_sessions.expires_at for auto-cleanup.
- **P2**: Split server.py into modules (auth.py, jobs.py, email_service.py, storage.py).
- **P2**: Customer-facing "track my job" page.

## Founding admin behavior
- The two founding emails are auto-promoted to admin on first sign-in via EITHER Google or email/password.
- Founders cannot be demoted by other admins (server enforces).
- Only founders can call `PUT /api/admin/users/{id}/role`.

## Open notes
- Original Stripe Connect (real payout flow) deferred — admin currently records payouts manually. Real Connect onboarding requires Stripe API key + Connect platform setup.
- Frontend untested end-to-end after iter 2 changes; backend fully validated.
