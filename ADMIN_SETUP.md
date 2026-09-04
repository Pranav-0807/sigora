# SIGORA Admin V1

## What is included

- Separate `/admin/login` and separate admin session
- Role-based access (`super_admin`, `admin`, `support`)
- 30-minute inactivity expiry for admin sessions
- CSRF protection on admin login and every admin write action
- Failed-login throttling (5 failed attempts per email/IP in 15 minutes)
- Admin audit trail with IP address
- User search, profile, plan, usage and account-state visibility
- Suspend, disable, reactivate, permanently delete
- Manual Premium grant/revoke and Razorpay subscription visibility
- Coupon creation/toggling
- AI and financial-feature adoption analytics
- In-app announcements for all/free/Premium audiences
- Support inbox and private admin notes
- System configuration/health view without exposing secrets

## First-time setup

1. Deploy the code normally. The app runs additive `ALTER TABLE ... IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS` migrations automatically.
2. Create a **dedicated Sigora account** for administration using the normal signup flow. A dedicated account is recommended instead of promoting your everyday user account.
3. In a Render Shell (or locally against the production database), run:

   `python promote_admin.py your-admin-email@example.com`

4. Open `/admin/login` and sign in with that account's existing password.

The promotion script changes the database `role` once. Runtime authorization does **not** compare an email address or rely on `ADMIN_EMAIL`.

## Roles

- `super_admin`: all controls, including permanent user deletion.
- `admin`: operations controls except permanent user deletion.
- `support`: read-only dashboard/users/analytics/support plus internal user notes.

V1 ships with the promotion helper setting `super_admin`. Additional role-management UI can be added later after there is more than one operator.

## Security notes

- Set a strong production `SECRET_KEY`.
- On HTTPS production, set `SESSION_COOKIE_SECURE=1`.
- Use a unique admin password and do not share the admin account.
- Admin passwords are stored using the same Werkzeug PBKDF2 hashing already used by Sigora.
- Admin login rate-limiting is database-backed so it works across multiple app workers.
- Permanent deletion is limited to `super_admin` and requires typing `DELETE`.
- System Health only checks configuration presence / DB connectivity. It never displays secrets.

## Recommended next security upgrade

Add TOTP/WebAuthn 2FA for admin accounts before giving admin access to anyone else. The role/session architecture in this build is ready for that layer.
