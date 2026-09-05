# Staff + Announcement Controls — 2026-09-05

Built directly on the user-supplied stable launch ZIP. No theme redesigns are included.

## Staff management
- New super-admin-only `/admin/staff` page.
- Search existing normal users and appoint them as `admin` or `support`.
- Change Admin/Support roles or demote them back to normal `user`.
- Super-admin accounts are protected; the acting super-admin cannot change their own role.
- Every role change is written to the existing admin audit log.

## Announcement admin controls
- Edit existing announcement title, message, and optional link.
- Tamil/Hindi translations are regenerated on edit.
- Original audience is locked after send, so editing cannot silently add/remove recipients.
- Super-admin-only global Delete removes the announcement plus all recipient alert copies in one transaction.
- Edit/delete operations are audit logged.

## User announcement cleanup
- A user can clear an individual announcement after it has been marked read.
- `Clear read` removes all read announcements only from that user's own inbox/history.
- Clearing a user's copy never affects other users or the global admin announcement.
