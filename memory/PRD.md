# Nosko Handyman — PRD (Iter 4)

## Iter 4 additions
- ✅ **Public tracking page** `GET /api/jobs/track/{job_id}` + `/track/:jobId` React route. No login. Safe subset only (name, service, address, status, ETA message, quoted amount, assigned handyman name, photos). Track link included in the customer confirmation email and shown on the success screen.
- ✅ **Auto-payouts on completion** — when admin sets job status to `completed`:
  - 15% to marketer (if referral_code valid)
  - 50% to assigned worker
  - remainder (35% or 50%) recorded as platform payout to the first founding admin (`noskotx@gmail.com`)
  - Recipients with `stripe_payouts_enabled=true` get a real `stripe.Transfer`; others recorded as `method='manual'`
  - **Race-safe**: atomic `findOneAndUpdate` ensures double-clicks don't fire duplicate payouts
  - Admin can pass `auto_payout=false` to skip
- ✅ 81/81 backend tests pass (15 new iter3 tests added on top of the iter1+iter2 regression suite).

## ⚠️ Owner action still required
1. **Enable Stripe Connect** at https://dashboard.stripe.com/connect (30s, free, one-time).
   - Until then, auto-payouts are recorded but not actually transferred to bank accounts.
2. **Real Gmail emails are working** — App Password `onglpbnyxgkwgvnb` confirmed sending welcome / quote / reset emails from `noskotx@gmail.com`.

## Cumulative feature set
- Cleaner DFW marketing site with portfolio + services grid + $25/swap + $50 visit minimum
- Anonymous quote request flow with photo upload + referral codes
- **Public job tracking page** (new)
- Worker / marketer signup wizards (profile → W9 → done)
- W9 (typed signature + PDF upload), stored in `w9_records`
- Worker dashboard: earnings cards (weekly/monthly/yearly/all-time), 12-week chart, assigned jobs table, payouts list, Stripe Connect card
- Marketer dashboard: referral code + copyable share URL, earnings + chart, Stripe Connect card
- Admin dashboard: stats, Jobs (assign worker, change status, see photos & quote), Workers/Marketers (pay), **Team** tab (founder-only role management), Portfolio CRUD, Site Settings editor (hero copy, contact, area, $ amounts)
- Hybrid auth: Google OAuth + email/password register/login/forgot/reset
- Account settings page for all users
- Gmail SMTP transactional emails: welcome, new-job to company, customer confirmation w/ track link, password reset
- Stripe Connect Express onboarding + transfers (waiting for owner to enable Connect)
- **Auto-payouts on job completion** (new) with 15/50/rest split

## Backlog (P0 → P2)
- **P0 (owner)**: Enable Stripe Connect at https://dashboard.stripe.com/connect.
- **P1**: `POST /api/stripe/webhook` to listen for `account.updated`, `transfer.failed`, `transfer.reversed` and reconcile payouts collection.
- **P1**: Offload SMTP to FastAPI BackgroundTasks (currently adds ~3s latency to POST /jobs).
- **P1**: Pydantic models on POST endpoints (raw dict → 500 on missing keys).
- **P2**: Split server.py into modules (1110+ lines).
- **P2**: TTL index on `user_sessions.expires_at`.
- **P2**: Customer "track my job" magic link with optional email-on-status-change notifications.
- **P2**: SMS notifications via Twilio (DFW homeowners are texters).
