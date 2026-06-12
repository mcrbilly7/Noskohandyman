# Nosko Handyman — PRD

## Product overview
Solo-handyman web app for Nosko (DFW). Customers submit quote requests with photos + preferred schedule. **Admin sets the price manually** and clicks **Send Quote** to email the customer (with editable subject + HTML). Customers track their job at `/track/:jobId` without logging in.

## Iter 8 changes (June 12, 2026) — Manual quoting + mobile admin + de-branding
- **Removed auto-pricing**: `POST /api/jobs` now creates jobs with `quoted_amount = null` and `quote_status = "pending"`. No more $50 floor stamped at creation.
- **3 new admin endpoints**:
  - `PUT /api/jobs/{job_id}/quote` — saves price, sets `quote_status = "draft"` (visible to admin only, NOT exposed publicly).
  - `POST /api/jobs/{job_id}/quote-preview` — returns `{subject, html, text}` populated with customer name, job_id, amount; admin can edit before sending.
  - `POST /api/jobs/{job_id}/send-quote` — sends the email (with admin-edited subject/html), sets `quote_status = "sent"` + `quote_sent_at`. Only 'sent' quotes are exposed on `/api/jobs/track/{id}`.
- **Track page hardened**: returns `quoted_amount = null` and `quote_status = "pending"|"draft"` until admin explicitly sends. Customer never sees a draft price.
- **Admin Dashboard Quote requests tab**: each job row now has:
  - `$` price input (`data-testid="quote-input-{job_id}"`)
  - "Save price" button (saves as draft)
  - "Send quote" button → opens modal with editable Subject + HTML editor + Preview tab + plain-text fallback. Confirm → emails customer + flips status to SENT (green badge with date).
- **TrackJobPage**: shows "Pending quote" until `quote_status === "sent"`.
- **Confirmation email rewrite**: post-submission email now says "we'll email you a custom quote within 24 hours" instead of pretending the request is already priced.
- **Mobile-friendly admin dashboard**: sidebar collapses behind a hamburger drawer below `lg` (1024px). New sticky topbar with MENU button + NOSKO logo + role tag. Stats grid reflows to 2×2 on mobile, tabs are horizontally scrollable, team table scrolls inside an overflow container, availability calendar drops to 1 month on phones, and admin page padding shrinks from `p-8` → `p-4`.
- **De-Emergent branded**:
  - Browser tab title is now "Nosko Handyman — DFW" (was "Emergent | Fullstack App").
  - Removed the bottom-right **"Made with Emergent"** badge and its loader script (`assets.emergent.sh/scripts/emergent-main.js`).
  - Removed embedded PostHog telemetry that was tied to the badge.
  - Updated meta description to Nosko's positioning.
  - Kept the Emergent OAuth flow in `lib/auth.jsx` (the invisible mechanism behind "Sign in with Google" — removing it would break login).

## Test status
- 16/16 backend pytest pass (`backend/tests/test_quote_flow.py`) — covers create/track/save/preview/send + auth-required negatives + 404s + validation.
- Frontend e2e verified by testing_agent_v3_fork (iteration_4): admin login → set price → save → send-quote modal → edit HTML → confirm → SENT badge → /track shows amount.

## Cumulative feature set
- Editable solo-handyman marketing site (Hero / Services with covers / How / Portfolio / Final CTA / Footer)
- Anonymous quote request with photo upload + calendar (blocked days + blocked weekdays) + time-slot picker
- **Manual admin quoting workflow** (set price → edit email → send) [NEW]
- Public job tracking page `/track/:jobId` (price only shown after admin sends quote)
- Hybrid auth (Google OAuth + email/password + forgot/reset)
- Founding admins: noskotx@gmail.com, nossonkosowsky32@gmail.com
- Admin tabs: Quote requests · Schedule · Team · Portfolio · Edit website
- Per-user account settings (name / phone / location / notify_email / password)
- Real Gmail SMTP emails (welcome, request-received confirmation, custom quote email, reset)
- Stripe Connect + auto-payouts logic dormant in backend (kept for possible re-pivot)

## Owner action for production
1. **Redeploy** to push iter8 (manual quoting) to https://noskotx.com.
2. Submit a test request from a different browser → check admin dashboard, enter a price, click Send Quote → verify the email lands in customer inbox.

## Backlog
- **P0 carry-over**: Landing page infinite-loading bug when portfolio/service images present — needs reproduction. Likely a silent API failure in `/portfolio` or `/site/settings` keeping the page hung.
- **P1**: Mobile responsiveness audit (LandingPage, AdminDashboard settings tab, JobRequestPage).
- **P1**: Move SMTP to BackgroundTasks (non-blocking).
- **P1**: Pydantic request models on POST endpoints.
- **P2**: Add Accept/Decline buttons on customer track page once quote is sent (customer can confirm or counter).
- **P2**: Split `server.py` (~1400 lines) into routers (auth, jobs, quotes, admin, settings).
- **P2**: SMS via Twilio.
- **P2**: Calendar export (ICS) of upcoming jobs.

## Architecture
- `frontend/` React + Tailwind + Shadcn UI. Pages in `src/pages/`, shared components in `src/components/shared/`.
- `backend/` FastAPI + Motor (MongoDB). Single `server.py` (target split: routers). Emergent object storage for uploads. Gmail SMTP for emails.
