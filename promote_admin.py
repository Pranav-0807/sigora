"""Promote an existing Sigora account to super_admin.
Usage: python promote_admin.py you@example.com
"""
import sys
from admin_features import ensure_admin_schema
from database import get_connection

if len(sys.argv) != 2:
    raise SystemExit("Usage: python promote_admin.py you@example.com")
email=sys.argv[1].strip().lower()
ensure_admin_schema()
conn=get_connection()
try:
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET role='super_admin',account_status='active' WHERE LOWER(email)=LOWER(%s) RETURNING id,name,email",(email,))
        row=cur.fetchone()
    if not row:
        raise SystemExit("No existing Sigora account found with that email. Create the account first.")
    conn.commit()
    print(f"Promoted {row[1]} <{row[2]}> to super_admin (user id {row[0]}).")
finally:
    conn.close()
