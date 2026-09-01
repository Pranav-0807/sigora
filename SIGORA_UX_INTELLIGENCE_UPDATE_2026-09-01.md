# SIGORA UX & Intelligence Update — 1 Sep 2026

## What changed
- Replaced the permanently visible desktop sidebar and crowded mobile nav with a single focused Menu button and slide-in navigation drawer.
- Grouped navigation into Money, Plan, Intelligence, Invest & Research, and Tools.
- Added English, Tamil and Hindi language selection in both the navigation drawer and Settings.
- Added server-side translation infrastructure for the navigation shell and key dashboard/settings experience.
- Added a dashboard “Know what happens next” intelligence surface powered by SIGORA’s deterministic Financial Intelligence engine (not LLM-invented numbers).
- Preserved the existing Intelligence page and Premium What-if Simulator as the deeper experience.

## Safety / regression scope
No payment, Razorpay webhook, Premium entitlement, coupon, authentication, market-history, Setu, database schema, or AI-limit behavior was intentionally changed.

## Validation
- Python compilation passed.
- All Jinja templates parsed successfully.
- verify_launch.py passed, including cancellation entitlement, navigation drawer, market-history guard, and Razorpay Offer linkage checks.
- git diff --check passed.

## Language scope
This release establishes the multilingual architecture and translates the navigation shell plus the key dashboard/settings experience. Long-form legal copy, user-generated content, market data, and some deeper feature-page copy remain in English to avoid unsafe machine-style translation of legal/financial wording. They can be translated in a dedicated reviewed content pass.
