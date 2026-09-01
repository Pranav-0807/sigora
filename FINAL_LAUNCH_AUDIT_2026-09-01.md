# SIGORA Final Launch Audit — 1 September 2026

Final regression pass covers:
- Premium cancellation: sends boolean `cancel_at_cycle_end: true`, preserves paid access through Razorpay `current_end`, and expires afterward via existing entitlement logic.
- Coupons: valid Sigora coupons require a Razorpay Offer ID and the Offer ID is sent to Razorpay when the subscription is created. Coupon redemption is recorded only after activation/charge webhook.
- Mobile tutorial: dedicated Tutorial control added to the mobile navigation because the desktop topbar is intentionally hidden on phones.
- Market research: sparse BSE history triggers NSE-history fallback; Sigora refuses to render a misleading 1–2 point diagonal chart if usable history remains unavailable.

No secrets are included in this release archive. Live payment behavior still depends on the merchant's Razorpay configuration and webhook delivery.
