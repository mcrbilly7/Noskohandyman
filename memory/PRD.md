# Nosko Handyman — PRD (Iter 5)

## Iter 5 — Solo handyman pivot
- Removed worker/marketer signup flows and links from public site (kept backend collections/endpoints dormant).
- Simplified nav: Services / How it works / Get a quote. Single CTA: "Get a quote".
- Admin tabs reduced to: **Quote requests · Team · Portfolio · Edit website**.
- "Edit website" expanded into a full site editor: brand & contact (incl. website_domain), hero copy + CTAs, services tiles (add/remove/edit each), how-it-works steps (add/remove/edit), programs copy (kept on backend for future), final CTA, footer tagline.
- Landing page is now 100% driven by site_settings — no hardcoded copy.
- Job request page no longer asks for referral code.
- AccountSettings cleaned up (removed Stripe Connect card since no workers/marketers).
- LandingPage now renders with safe defaults if /api/site/settings is slow/fails — **no more infinite loading**.
- Added 20s axios timeout so calls fail fast instead of hanging.
- All 81 backend regression tests still pass.

## Production deployment
- Custom domain (preview & prod):
  - PREVIEW: https://nosko-handyman.preview.emergentagent.com
  - PRODUCTION: https://noskotx.com (deployed via Emergent platform)
- Production frontend env (REACT_APP_BACKEND_URL) must point to the deployed production backend, not the preview URL.
- Production backend env must include SMTP_*, STRIPE_API_KEY, FOUNDING_ADMINS, EMERGENT_LLM_KEY copied from preview.

## Cumulative feature set (current)
- Public landing page (Hero / Services / How it works / Portfolio / Final CTA / Footer) - 100% editable from admin
- Anonymous quote request flow with photo upload
- Public job tracking page at `/track/:jobId`
- Hybrid auth: Google OAuth + email/password + forgot/reset password
- Founding admins auto-promoted: noskotx@gmail.com, nossonkosowsky32@gmail.com
- Admin "Team" tab (founder-only role management)
- Account settings (every user)
- Full site editor (admin "Edit website" tab)
- Real Gmail SMTP transactional emails: welcome / quote-request to company / customer confirmation w/ track link / password reset
- Auto-payouts on job completion (dormant — no workers/marketers signing up via UI now; still callable via API if needed)
- Stripe Connect endpoints intact (dormant)

## Backlog (P0 → P2)
- **P1**: Pydantic models on POST endpoints (raw dict → 500 on missing fields).
- **P1**: Move SMTP to FastAPI BackgroundTasks (currently adds ~3s latency to POST /jobs).
- **P2**: Customer SMS notifications via Twilio.
- **P2**: TTL index on user_sessions.expires_at.
- **P2**: Split server.py into modules.
- **P2 (optional)**: Remove dormant worker/marketer/payout backend endpoints if owner confirms permanent solo-handyman model.

## Notes for future sessions
- The admin "Edit website" tab is the source of truth for landing page copy. Owner can edit everything from there.
- All admin tabs work as designed; founder edits visible only to noskotx@gmail.com and nossonkosowsky32@gmail.com.
- If owner wants worker/marketer back, just restore the routes in `/app/frontend/src/App.js` and re-link from nav/landing.
