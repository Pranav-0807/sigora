# Sigora Web

Personal finance dashboard built with Flask and PostgreSQL.

## Launch features

- Settings and account preferences
- Mobile-first login/signup and responsive navigation
- Redesigned Budgets and Goals with interactive AI detail panels
- Gamification: XP, levels, streaks and badges
- Goal/budget/transaction celebration moments
- Automatic transaction categorization from descriptions
- CSV and Excel (`.xlsx`) statement import with duplicate detection
- In-app financial alerts with optional email delivery
- ₹149/month Premium with Razorpay recurring-subscription checkout, signed verification, webhooks, cancellation, and coupon/offer support

## Local setup

1. Create a virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and add local credentials.
4. Make sure PostgreSQL is available and `DATABASE_URL` is set.
5. Run the app with Flask/Gunicorn.

The application automatically creates the launch-feature columns/tables on first authenticated database access. `schema.sql` also contains the complete schema for fresh databases.

## Deployment notes

Set `DATABASE_URL` and `SECRET_KEY` in the deployment environment. Do not commit `.env` or API keys. Optional email alerts require `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM`.


## Launch configuration
- Free AI allowance: 5 analyses/month, 2/day.
- Premium AI allowance: 30 analyses/month, 5/day.
- SMS alerts: intentionally disabled during beta; the UI shows a Coming Soon message.
- Support email: set `SIGORA_SUPPORT_EMAIL` when a dedicated inbox exists.
- Razorpay credentials are environment-only and can be added when the merchant account is ready.
- Gemini Paid Tier can be enabled later without changing the application-side usage controls.
