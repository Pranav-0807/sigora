# SIGORA Announcements V2.1

Adds a permanent announcement bell to the authenticated top bar and drawer.

- Bell is always visible.
- Badge appears only when unread admin announcements exist.
- `/announcements` provides localized announcement history.
- Existing animated popup remains the first-time unread experience.
- Read state is per user through the existing `alerts.is_read` field.
- Tamil/Hindi versions use the translations already generated when the admin sends the English announcement.
