# Sigora Razorpay subscription setup

The app now uses Razorpay Subscriptions for the ₹149/month Premium plan.

## Required environment variables (local `.env` and Render)

- `RAZORPAY_KEY_ID` — use the Test key while testing, Live key after activation.
- `RAZORPAY_KEY_SECRET` — matching secret. Never commit it.
- `RAZORPAY_PLAN_ID` — the Plan ID shown for the Sigora Premium ₹149 / Every Month plan.
- `RAZORPAY_WEBHOOK_SECRET` — a strong secret you choose when creating the webhook in Razorpay.

## Webhook

Create a Razorpay webhook pointing to:

`https://YOUR-SIGORA-DOMAIN/razorpay/webhook`

Subscribe at minimum to:

- `subscription.activated`
- `subscription.charged`
- `subscription.cancelled`
- `subscription.halted`
- `subscription.completed`

Use the exact same webhook secret in Razorpay and `RAZORPAY_WEBHOOK_SECRET` on Render.

## Test flow

1. Keep Razorpay in Test Mode.
2. Put the TEST key ID/secret and TEST plan ID in Render.
3. Open Sigora Premium and start checkout.
4. Complete a Razorpay test subscription payment.
5. Checkout signature is verified server-side.
6. Premium becomes active only after a signed Razorpay webhook confirms activation/charge.
7. Test cancellation; it is requested for the end of the current billing cycle.

## Coupons / offers

Sigora coupons can store a Razorpay `offer_id`. The offer itself must be configured in Razorpay with the intended discount duration (for example first payment/month only). Sigora no longer consumes the coupon when checkout is merely created; redemption is recorded only after Razorpay confirms activation/charge.

## Going live

After KYC/live activation, create/confirm the corresponding Live plan and Live offers, then replace the four Razorpay environment variables with their Live values. Test Mode and Live Mode IDs/keys are separate.
