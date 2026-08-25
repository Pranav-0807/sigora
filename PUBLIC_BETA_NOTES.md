# Sigora Public Beta – final launch notes

- Password change is active and verifies the current password before updating the password hash.
- Email delivery uses the existing SMTP configuration.
- Budget alerts at 80%+ and goal-deadline warnings can now trigger email delivery when email alerts are enabled.
- Duplicate alert fingerprints prevent repeated email spam for the same threshold/deadline alert.
- Bank Accounts is intentionally shown as Coming Soon until regulated Account Aggregator/FIU provider onboarding is available.
- Statement import remains the active bank-data ingestion path for public beta.

- Deleting budgets/goals now removes their stale dashboard alerts.
- Alert email delivery is tracked with `email_sent_at`; pre-existing unsent alerts retry safely after SMTP becomes available.
