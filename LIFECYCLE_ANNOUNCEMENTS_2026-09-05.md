# Sigora built-in lifecycle announcements — 5 Sep 2026

- New Free accounts receive one built-in welcome announcement after signup.
- The Free welcome explains Sigora and links to Premium.
- A user receives the Premium welcome only when `premium_started_at` is set for the first time.
- Razorpay webhook retries/renewals cannot duplicate the Premium welcome because the alert fingerprint is unique per user.
- Manual admin Premium grants also trigger the welcome only on the user's first-ever Premium activation.
- Both messages contain stored English, Tamil and Hindi variants and therefore follow the user's current Sigora language whenever viewed.
- Built-in lifecycle definitions are hidden from the Admin Announcements editor so they cannot be accidentally edited/deleted as broadcast announcements.
- User read/clear behavior works exactly like other announcements.
