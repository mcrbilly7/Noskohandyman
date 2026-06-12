# Nosko Handyman — PRD

## Product overview
Solo-handyman web app for Nosko (DFW). Customers submit quote requests with photos, optional promo code, and a preferred schedule. Admin sets the price manually and clicks Send Quote (with editable subject/HTML, template picker, optional line-item breakdown). Customers track their job at `/track/:jobId` without logging in. Email list signup on landing page auto-issues one-time discount codes. Admin can broadcast emails to the list and manage codes, templates, subscribers, schedule, portfolio, and site content from a single dashboard.

## Latest changes (Iter 9 — June 12, 2026)
### Email list + discount codes + templates + blasts
- **Newsletter section on landing page** (above footer, id=`email-signup`). Email submit → instant card with the generated code + auto-emails it. Re-subscribing returns the existing unused code or a "welcome back" message.
- **Discount codes** (one-time, single-use):
  - Auto-generated on email signup (default 15% off — configurable in Settings).
  - Admin can manually create codes with custom % off, assign to an email, add notes.
  - Admin can edit code string, % off, notes; can reset usage; can delete.
  - Validation endpoint (`POST /api/discount-codes/validate`) used by the quote-request form.
  - Code is marked used **only after** the admin clicks Send Quote, not at job submit (prevents accidental burns).
- **Promo code field** on `/request` with Apply button, inline validate, green/red feedback.
- **Polished success screen** (`/request` after submit) — big green check, "Quote request submitted." title, job ID + email cards, tracking link block, 3-step "What happens next" grid, promo strip if a code was applied.
- **Email templates** (`/admin > Email templates`): 3 defaults seeded ("Friendly quote" ★, "Formal", "Quick price"). Full CRUD + single-default invariant. Variables supported: `{{customer_name}} {{first_name}} {{service_type}} {{address}} {{amount}} {{job_id}} {{track_url}} {{contact_email}} {{preferred_date}} {{breakdown_block}}`. Live preview with sample data.
- **Send Quote modal upgraded**: template picker buttons + collapsible **Quote breakdown** editor (add rows with label + amount, subtotal display, mismatch warning vs. total). Selecting a template re-renders subject/HTML; manual edits persist until "Reset edits".
- **Email blast** (`/admin > Email list`): compose with Subject + HTML editor + Edit/Preview tabs, recipient count preview, Send to N. Past blasts listed below with sent/failed counts. Subscriber table shows email, code, % off, USED/UNUSED, joined date, delete.
- **Settings**: new "Email signup & discount" section — auto-percent, enable/disable section, overline/heading/subheading.

### Mobile-friendly admin (Iter 8)
- Sidebar collapses behind hamburger drawer below 1024px; sticky topbar with MENU button + NOSKO logo.
- Stats reflow to 2×2 on mobile, tabs scroll horizontally, team table inside overflow container, calendar drops to 1 month on phones.

### De-Emergent branding (Iter 8)
- Removed "Made with Emergent" badge + loader script + PostHog telemetry.
- Browser title "Nosko Handyman — DFW", meta description Nosko-positioned.
- Kept Emergent OAuth in `lib/auth.jsx` (invisible Google sign-in mechanism).

### Manual quoting (Iter 8)
- `POST /api/jobs` no longer auto-prices (`quoted_amount = null`, `quote_status = "pending"`).
- 3 admin endpoints: `PUT /jobs/{id}/quote` (save draft), `POST /jobs/{id}/quote-preview` (returns subject+html+text), `POST /jobs/{id}/send-quote` (emails customer, marks SENT, marks promo used).
- Track endpoint only exposes price after `quote_status === "sent"`.

## Test status
- **37 backend pytest passing** (16 quote flow + 21 email/promo flow) across `/app/backend/tests/`.
- Frontend e2e verified by testing_agent + manual screenshots (iteration_4.json passed for quote flow; iter 9 UI screenshot confirms 3 new admin tabs + landing newsletter live).

## API endpoint summary
| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /api/subscribers` | public | Sign up to email list, returns code |
| `GET /api/subscribers` | admin | List with hydrated code/usage |
| `DELETE /api/subscribers/{id}` | admin | Remove subscriber |
| `POST /api/discount-codes/validate` | public | Used by quote form |
| `GET/POST/PUT/DELETE /api/discount-codes` | admin | Manage codes |
| `GET/POST/PUT/DELETE /api/email-templates` | admin | Manage quote templates |
| `POST /api/email-blasts/preview` | admin | Returns recipient_count |
| `POST /api/email-blasts` | admin | Send to all subscribers |
| `GET /api/email-blasts` | admin | List past blasts |
| `POST /api/jobs` | public | Accepts `promo_code` (validates + stores promo_meta) |
| `PUT /api/jobs/{id}/quote` | admin | Save draft price |
| `POST /api/jobs/{id}/quote-preview` | admin | Render `{template_id, line_items}` → subject+html |
| `POST /api/jobs/{id}/send-quote` | admin | Send email, mark code used |

## Admin action for production
1. **Save to GitHub** (one click on the chat input — that's how repo push happens; main agent can't push directly).
2. **Redeploy** in the Emergent UI to push Iter 9 to https://noskotx.com.
3. Try the flow end-to-end: sign up to your own email list with a test address → check inbox for the discount code → submit a quote request using that code → in admin, set a price, click Send Quote, pick a template, add line items, send → confirm the customer email includes the breakdown and the code is marked USED.

## Backlog
- 🟡 **P1**: Landing page infinite-loading bug when portfolio/service images uploaded — could not reproduce in preview. Needs production repro.
- 🟡 P1: Mobile audit of public LandingPage + JobRequestPage (only admin was done).
- 🟢 P2: Split `server.py` (now ~1850 lines) into routers (auth, jobs, quotes, subscribers, codes, templates, blasts, admin).
- 🟢 P2: Move SMTP to BackgroundTasks (blast endpoint is sync today).
- 🟢 P2: Pydantic request models on POST endpoints.
- 🟢 P2: Customer Accept/Decline buttons on track page after quote sent.
- 🟢 P2: SMS / push notifications when a new request hits the inbox.
- 🟢 P2: ICS calendar export of upcoming jobs.

## Architecture
- `frontend/` React + Tailwind + Shadcn UI. Admin sub-tabs split into `src/components/admin/*Tab.jsx`. Shared bits in `src/components/shared/`. Pages in `src/pages/`.
- `backend/` FastAPI + Motor (MongoDB). Single `server.py` (target: split into routers). Emergent object storage for uploads. Gmail SMTP for emails.

## Collections (MongoDB)
- `users` — auth
- `user_sessions`, `password_reset_tokens` — auth helpers
- `jobs` — now includes `promo_code, promo_meta, quote_line_items, quote_template_id, quote_status, quote_sent_at`
- `site_settings` — includes newsletter_* + signup_default_percent_off
- `availability` — blocked_dates + blocked_weekdays
- `portfolio` — admin uploads
- `subscribers` — {sub_id, email (unique), subscribed_at, source, discount_code_id}
- `discount_codes` — {code_id, code (unique), percent_off, email?, issued_at, used_at?, used_on_job_id?, created_by, notes}
- `email_templates` — {template_id, name, subject_template, html_template, is_default}
- `email_blasts` — {blast_id, subject, html, text, sent_at, recipient_count, sent_count, failed_count}
