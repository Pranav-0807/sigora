# Sigora V1.1 Consolidated Launch Build

Included in this build:
- Premium price: INR 149/month, configuration-driven.
- Razorpay-ready checkout that stays dormant until credentials/plan ID are configured.
- Coupon administration at `/admin/coupons` for the configured `ADMIN_EMAIL`.
- Support email configuration through `SIGORA_SUPPORT_EMAIL`.
- Signup country selection with automatic default currency and Settings country/currency override.
- Goal Add Savings flow.
- Universal transaction importer for CSV, XLSX, XLS and PDF, including encrypted PDFs.
- Automatic header/column detection, debit/credit/amount normalization, duplicate detection and import preview.
- Batch database import to avoid the Render worker/resource issue seen with large imports.
- Import file/row safety limits and friendly 413/500 handling.
- Gemini daily/monthly request limits, 429 handling, and an application-level monthly estimated-cost guardrail.
- SMS remains intentionally disabled.
- Transaction CSV/XLSX export.
- Existing gamification, reports, budgets, goals, tutorial and support-message flow retained.

External setup remains configuration-only: Razorpay credentials/plan/webhook secret, SMTP/support email, Gemini API key and production database URL.
