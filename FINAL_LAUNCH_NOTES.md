# Sigora final launch safeguards

## Gemini / AI
- AI calls are no longer generated automatically just by opening Budgets or Goals. Users explicitly request them.
- Default limits: Free 5/month + 2/day; Premium 30/month + 5/day.
- `AI_GLOBAL_MONTHLY_REQUEST_LIMIT` adds an app-wide emergency cap (default 2000 requests/month).
- `AI_MONTHLY_BUDGET_USD` remains a per-user application guardrail estimate, not a Google billing budget.

## Premium / Razorpay
- Premium is activated only by verified Razorpay subscription webhooks.
- Expired Premium is automatically treated as inactive and cleaned up in the database.
- Cancel-at-cycle-end state is stored so users cannot repeatedly request cancellation.
- `RAZORPAY_TOTAL_COUNT` controls the subscription cycle count (default 120).

## Coupons
- Checkout coupons must have a Razorpay Offer ID; otherwise Sigora rejects the coupon rather than displaying a fake discount.
- Coupon usage is recorded only after Razorpay confirms activation/payment.
- Recent pending coupon reservations are considered when enforcing max uses.
- “First month only” must be configured on the corresponding Razorpay Offer for one billing cycle.
