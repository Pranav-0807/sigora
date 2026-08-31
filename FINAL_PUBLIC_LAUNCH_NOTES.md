# SIGORA — Final Public Launch Package

Prepared: 31 August 2026

## Included launch changes

- Updated in-app 6-step interactive tutorial covering transactions/imports, budgets/goals, intelligence, investments, AI, settings and Premium.
- Updated Premium/support/legal copy for live recurring billing.
- Razorpay subscription creation now sends `customer_notify` as a JSON boolean, matching current Razorpay API documentation.
- Razorpay subscription failures are logged with HTTP status, provider error code and description without logging credentials.
- Existing verified webhook signature flow remains the source of truth for Premium activation/deactivation.
- Existing ₹149 INR monthly plan environment integration retained.
- Existing BSE historical chart fallback retained.

## Production environment required

`SECRET_KEY`, `DATABASE_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_PLAN_ID`, `RAZORPAY_WEBHOOK_SECRET`, plus configured email/AI variables. Secrets must remain in Render and must never be committed.

## Before public announcement

1. Deploy this package.
2. Complete one controlled ₹149 live subscription.
3. Confirm Razorpay shows the subscription/payment.
4. Confirm Sigora Premium becomes active after the signed webhook.
5. Confirm cancellation-at-cycle-end works on the controlled account.

Bank Account Aggregator connectivity remains gated until provider/FIU onboarding and production credentials are complete.
