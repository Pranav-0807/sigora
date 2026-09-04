# SIGORA Announcements V2 — 2026-09-04

- Admin authors announcements in English.
- On send, SIGORA translates the title and message once into Tamil and Hindi using the configured Gemini provider.
- Translation failures never block delivery; English is used as a safe fallback.
- Users see unread admin announcements in a terminal-style modal with a character-by-character typing animation.
- The popup uses the user's current SIGORA language setting (English / Tamil / Hindi).
- Closing the popup or pressing “Got it” marks that user's alert as read, so it does not repeatedly interrupt them.
- Existing dashboard alert cards also localize newly-created admin announcements.
- Audience targeting (all / free / premium) remains enforced by the existing admin announcement sender.
- Existing announcements created before this migration remain valid; they fall back to English because they do not have stored translations / announcement linkage.
