# Session + Email Check

## Home / login navigation
The landing-page primary button now respects the current Flask session:
- signed out -> `/login`
- signed in -> `/dashboard`

This fixes the previous behavior where a signed-in user could click Home and then "Enter Sigora" and be sent back to the login page even though the session still existed.

## Email delivery
No email-sending code was changed in this patch. The current Resend integration is successfully accepted by Resend and the recipient mail server has returned a successful SMTP delivery response in prior tests. If Gmail does not surface the message, move the sender from `onboarding@resend.dev` to a verified custom domain in Resend before public launch.

No `.env` or API secrets are included in this package.
