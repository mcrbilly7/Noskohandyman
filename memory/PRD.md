# Nosko Handyman — PRD (Iter 7)

## Iter 7 changes
- **CORS hardened** for cross-origin credentialed requests. The old config used `allow_origins=["*"]` with `allow_credentials=True` — browsers reject that combo for any origin that wasn't already cached. Now uses `allow_origin_regex=".*"` so the server echoes back the request origin (works for noskotx.com from any device).
- **Owner availability schedule**:
  - `GET /api/availability` (public) — returns `{blocked_dates: [YYYY-MM-DD]}`.
  - `PUT /api/availability` (admin) — replaces full set.
  - Admin Dashboard new **Schedule** tab with 2-month calendar; click any future day to toggle blocked (red-strike). Blocked count + clear-all sidebar.
  - Customer quote calendar (on `/request`) loads blocked dates and disables them (unclickable).
  - `POST /api/jobs` server-side guard: rejects with 400 if `preferred_date` is in blocked list (defense in depth).
- **Service tile cover images**:
  - Each `services[]` entry on site_settings supports `image_path`.
  - Admin "Edit website" → Services tiles: per-tile FileUploader for cover image (140px slot).
  - Landing page renders 4:3 cover image at top of each service tile when set.
- **Admin sidebar cleaned**: removed Workers/Marketers/Jobs/Portfolio links (those are tabs inside Command center now). Sidebar shows: Command center · My account.

## Test status
- **95/95 backend tests pass** (81 prior + 14 new iter7). See `/app/test_reports/`.
- Lint warnings about pre-existing apostrophe-escapes/old hooks are not regressions; new file `AvailabilityEditor.jsx` is clean.

## Cumulative current feature set
- Editable solo-handyman marketing site (Hero / Services with covers / How / Portfolio / Final CTA / Footer)
- Anonymous quote request with photo upload + calendar (blocked days disabled) + time-slot picker
- Public job tracking page `/track/:jobId`
- Hybrid auth (Google OAuth + email/password + forgot/reset)
- Founding admins: noskotx@gmail.com, nossonkosowsky32@gmail.com
- Admin tabs: Quote requests · **Schedule** · Team · Portfolio · Edit website
- Per-user account settings (name / phone / location / notify_email / password)
- Real Gmail SMTP emails (welcome, quote, reset, track link)
- Stripe Connect + auto-payouts logic dormant in backend

## Owner action for production
1. **Redeploy** to push iter7 (CORS fix + availability + service covers + sidebar cleanup) to https://noskotx.com. The CORS fix is the critical one for "doesn't work on other devices".
2. After redeploy, ask a friend to test on a fresh device — submitting a quote should work without sign-in.
3. If still broken after redeploy: contact Emergent Support — production ingress may need its own CORS allow.

## Backlog
- P1: Move SMTP to BackgroundTasks
- P1: Pydantic request models on POST endpoints
- P2: SMS via Twilio
- P2: Calendar export (ICS) of upcoming jobs for the owner
- P2: Customer-facing "edit my scheduled time" via track page
