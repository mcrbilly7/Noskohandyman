# Nosko Handyman — PRD (Iter 6)

## Iter 6 changes
- **Removed $25 set-price entirely** from defaults: `outlet_price` default is now `0` (= hidden on landing & request pages). Visit minimum stays at $50.
- **Landing**: single bold "$50 Visit minimum" card replaces the two-card layout. Updated subtitle, "Anything a handyman does — we do." section heading, services tile copy (no more "$25 flat").
- **Calendar / time-slot picker on quote request**:
  - Customer picks a date (no past dates) + time window (Morning / Afternoon / Evening / Flexible).
  - Backend stores `preferred_date` (ISO date string) + `preferred_time_slot` on the job.
  - Public tracking page shows scheduled time.
  - Admin job row displays preferred time as a black/yellow chip.
- **Sparse settings doc**: `GET /api/site/settings` now merges stored values over `SiteSettings()` defaults — so admin edits can be sparse and missing fields fall back gracefully (fixes the "blank hero / blank CTA" bug).
- All 81/81 backend tests pass.

## Editable from admin "Edit website" tab
- Hero title/subtitle + CTA labels
- Visit minimum $ and outlet/swap $ (set outlet=0 to hide that card)
- Services tiles (add/edit/remove)
- How-it-works steps (add/edit/remove)
- Section headings & overlines
- Programs copy (dormant on landing, kept for future)
- Final CTA strip + footer tagline
- Website domain, contact phone & email, service area

## Cumulative feature set (current)
- Cleaner DFW marketing site: Hero / Services / How / Portfolio / Final CTA / Footer — all editable
- **Anonymous quote request** with photo upload + **calendar & time-slot picker**
- **Public job tracking page** `/track/:jobId` showing status, ETA, scheduled time, address, quote
- Hybrid auth: Google OAuth + email/password + forgot/reset password
- Founding admins (`noskotx@gmail.com`, `nossonkosowsky32@gmail.com`) auto-promoted; founder-only role management in admin "Team" tab
- Account settings page for every user
- Admin: Quote requests / Team / Portfolio / Edit website
- Gmail SMTP transactional emails (welcome, quote-request to owner, customer confirmation w/ track link, password reset)
- Stripe Connect + auto-payouts logic remain in backend (dormant)

## Action items for owner (production)
- **Redeploy** to push iter5 + iter6 changes to https://noskotx.com.
- Enable Stripe Connect at https://dashboard.stripe.com/connect (if/when re-introducing payouts).
- DNS / custom domain steps in the previous summary.

## Backlog
- **P1**: Pydantic models on POST endpoints (raw dict → 500 on missing fields).
- **P1**: Move SMTP to FastAPI BackgroundTasks (sync sends add ~3s latency).
- **P2**: SMS notifications via Twilio (DFW homeowners are texters).
- **P2**: Customer-facing "edit my scheduled time" link in confirmation email.
- **P2**: Admin can override preferred time + auto-send "scheduled for X" email.
- **P2**: Remove dormant worker/marketer/payout backend endpoints if owner confirms permanent solo-handyman model.
