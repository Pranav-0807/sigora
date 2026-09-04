"""Administrative controls for Sigora.

Admin authorization is role-based and uses a separate admin session in app.py.
No request-time authorization depends on a hard-coded admin email.
"""
from datetime import datetime, timedelta
import os

from database import get_connection

_ADMIN_SCHEMA_READY = False


def ensure_admin_schema():
    global _ADMIN_SCHEMA_READY
    if _ADMIN_SCHEMA_READY:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(30) NOT NULL DEFAULT 'user'")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS account_status VARCHAR(30) NOT NULL DEFAULT 'active'")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMP")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason TEXT")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(account_status)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_audit_log (
                    id BIGSERIAL PRIMARY KEY,
                    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    action VARCHAR(100) NOT NULL,
                    target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    details TEXT,
                    ip_address VARCHAR(80),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at DESC)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_login_attempts (
                    id BIGSERIAL PRIMARY KEY,
                    email VARCHAR(255),
                    ip_address VARCHAR(80),
                    success BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_lookup ON admin_login_attempts(email, ip_address, created_at DESC)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_notes (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    note TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_announcements (
                    id BIGSERIAL PRIMARY KEY,
                    admin_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    title VARCHAR(180) NOT NULL,
                    message TEXT NOT NULL,
                    title_ta VARCHAR(180),
                    message_ta TEXT,
                    title_hi VARCHAR(180),
                    message_hi TEXT,
                    link VARCHAR(255),
                    audience VARCHAR(30) NOT NULL DEFAULT 'all',
                    recipients INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS title_ta VARCHAR(180)")
            cur.execute("ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS message_ta TEXT")
            cur.execute("ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS title_hi VARCHAR(180)")
            cur.execute("ALTER TABLE admin_announcements ADD COLUMN IF NOT EXISTS message_hi TEXT")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payment_events (
                    id BIGSERIAL PRIMARY KEY,
                    event_type VARCHAR(100) NOT NULL,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    payment_id VARCHAR(120),
                    order_id VARCHAR(120),
                    subscription_id VARCHAR(120),
                    amount NUMERIC(18,2),
                    currency VARCHAR(10),
                    status VARCHAR(60),
                    source VARCHAR(30) NOT NULL DEFAULT 'webhook',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_created ON payment_events(created_at DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_payment_events_user ON payment_events(user_id)")
        conn.commit()
        _ADMIN_SCHEMA_READY = True
    finally:
        conn.close()


def get_admin_identity(user_id):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id,name,email,role,account_status,last_login_at
                FROM users WHERE id=%s
            """, (user_id,))
            r = cur.fetchone()
        if not r:
            return None
        return {"id": r[0], "name": r[1], "email": r[2], "role": r[3], "account_status": r[4], "last_login_at": r[5]}
    finally:
        conn.close()


def get_user_access_state(user_id):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT role,account_status,suspended_reason FROM users WHERE id=%s", (user_id,))
            r = cur.fetchone()
        return {"role": r[0], "account_status": r[1], "suspended_reason": r[2]} if r else None
    finally:
        conn.close()


def touch_last_login(user_id):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login_at=CURRENT_TIMESTAMP WHERE id=%s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def admin_login_blocked(email, ip_address, window_minutes=15, max_failures=5):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM admin_login_attempts
                WHERE success=FALSE
                  AND created_at > CURRENT_TIMESTAMP - (%s * INTERVAL '1 minute')
                  AND (LOWER(email)=LOWER(%s) OR ip_address=%s)
            """, (window_minutes, email, ip_address))
            return int(cur.fetchone()[0]) >= max_failures
    finally:
        conn.close()


def record_admin_login(email, ip_address, success):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO admin_login_attempts(email,ip_address,success) VALUES(%s,%s,%s)", (email, ip_address, success))
            cur.execute("DELETE FROM admin_login_attempts WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'")
        conn.commit()
    finally:
        conn.close()


def audit(admin_user_id, action, target_user_id=None, details=None, ip_address=None):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO admin_audit_log(admin_user_id,action,target_user_id,details,ip_address)
                           VALUES(%s,%s,%s,%s,%s)""", (admin_user_id, action, target_user_id, details, ip_address))
        conn.commit()
    finally:
        conn.close()


def dashboard_metrics():
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE is_premium), COUNT(*) FILTER (WHERE account_status='active'), COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') FROM users WHERE role='user'")
            u = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM transactions")
            tx = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(requests),0) FROM ai_global_usage WHERE month_start=DATE_TRUNC('month',CURRENT_DATE)::date")
            ai = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM support_messages WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'")
            support = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM users WHERE role='user' AND last_login_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'")
            active_30 = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM admin_audit_log")
            audits = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM admin_audit_log WHERE action='user_deleted' AND created_at >= CURRENT_DATE - INTERVAL '30 days'")
            deleted_30d = cur.fetchone()[0]
            cur.execute("""SELECT DATE(created_at),COUNT(*) FROM users WHERE role='user' AND created_at >= CURRENT_DATE - INTERVAL '13 days' GROUP BY DATE(created_at) ORDER BY DATE(created_at)""")
            signups = cur.fetchall()
        total = int(u[0] or 0)
        premium = int(u[1] or 0)
        return {
            "total_users": total, "premium_users": premium, "free_users": max(total-premium, 0),
            "enabled_users": int(u[2] or 0), "new_7d": int(u[3] or 0), "transactions": int(tx or 0),
            "ai_month": int(ai or 0), "support_30d": int(support or 0), "active_30d": int(active_30 or 0),
            "audit_events": int(audits or 0), "deleted_30d": int(deleted_30d or 0), "premium_conversion": round((premium/total*100),1) if total else 0,
            "signup_series": [(str(r[0]), int(r[1])) for r in signups]
        }
    finally:
        conn.close()


def recent_activity(limit=30):
    ensure_admin_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT a.id,a.action,a.target_user_id,a.details,a.ip_address,a.created_at,u.name,u.email
                           FROM admin_audit_log a LEFT JOIN users u ON u.id=a.admin_user_id
                           ORDER BY a.created_at DESC LIMIT %s""", (limit,))
            rows = cur.fetchall()
        return [{"id":r[0],"action":r[1],"target_user_id":r[2],"details":r[3],"ip":r[4],"created_at":r[5],"admin_name":r[6],"admin_email":r[7]} for r in rows]
    finally:
        conn.close()


def list_users(search="", status="", plan="", limit=200):
    ensure_admin_schema()
    conn = get_connection()
    clauses=["role='user'"]
    params=[]
    if search:
        clauses.append("(LOWER(name) LIKE LOWER(%s) OR LOWER(email) LIKE LOWER(%s))")
        q=f"%{search}%"; params.extend([q,q])
    if status in {"active","suspended","disabled"}:
        clauses.append("account_status=%s"); params.append(status)
    if plan == "premium": clauses.append("is_premium=TRUE")
    if plan == "free": clauses.append("is_premium=FALSE")
    params.append(limit)
    try:
        with conn.cursor() as cur:
            cur.execute(f"""SELECT id,name,email,country,currency,created_at,last_login_at,is_premium,
                             premium_expires_at,razorpay_subscription_status,account_status
                             FROM users WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT %s""", params)
            rows=cur.fetchall()
        return [{"id":r[0],"name":r[1],"email":r[2],"country":r[3],"currency":r[4],"created_at":r[5],"last_login_at":r[6],"is_premium":r[7],"premium_expires_at":r[8],"subscription_status":r[9],"account_status":r[10]} for r in rows]
    finally:
        conn.close()


def user_detail(user_id):
    ensure_admin_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,name,email,country,currency,created_at,last_login_at,is_premium,premium_started_at,premium_expires_at,
                           razorpay_subscription_id,razorpay_subscription_status,premium_cancel_at_cycle_end,account_status,suspended_at,suspended_reason
                           FROM users WHERE id=%s""",(user_id,)); r=cur.fetchone()
            if not r: return None
            cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id=%s",(user_id,)); tx=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM budgets WHERE user_id=%s",(user_id,)); budgets=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM goals WHERE user_id=%s",(user_id,)); goals=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM investments WHERE user_id=%s",(user_id,)); investments=cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM investment_watchlist WHERE user_id=%s",(user_id,)); watchlist=cur.fetchone()[0]
            cur.execute("SELECT month_requests,day_requests,updated_at FROM ai_usage WHERE user_id=%s",(user_id,)); ai=cur.fetchone()
            cur.execute("SELECT id,note,created_at,admin_user_id FROM admin_notes WHERE user_id=%s ORDER BY created_at DESC",(user_id,)); notes=cur.fetchall()
        return {"id":r[0],"name":r[1],"email":r[2],"country":r[3],"currency":r[4],"created_at":r[5],"last_login_at":r[6],"is_premium":r[7],"premium_started_at":r[8],"premium_expires_at":r[9],"razorpay_subscription_id":r[10],"subscription_status":r[11],"cancel_at_end":r[12],"account_status":r[13],"suspended_at":r[14],"suspended_reason":r[15],"transactions":tx,"budgets":budgets,"goals":goals,"investments":investments,"watchlist":watchlist,"ai_month":(ai[0] if ai else 0),"ai_day":(ai[1] if ai else 0),"ai_updated":(ai[2] if ai else None),"notes":[{"id":n[0],"note":n[1],"created_at":n[2],"admin_user_id":n[3]} for n in notes]}
    finally: conn.close()


def set_account_status(user_id, status, reason=None):
    if status not in {"active","suspended","disabled"}: raise ValueError("Invalid account status")
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE users SET account_status=%s,
                           suspended_at=CASE WHEN %s='suspended' THEN CURRENT_TIMESTAMP ELSE NULL END,
                           suspended_reason=CASE WHEN %s='suspended' THEN %s ELSE NULL END
                           WHERE id=%s AND role='user'""",(status,status,status,reason,user_id))
        conn.commit()
    finally: conn.close()


def set_user_premium(user_id, active):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            if active:
                cur.execute("""UPDATE users SET is_premium=TRUE,premium_started_at=COALESCE(premium_started_at,CURRENT_TIMESTAMP),
                               premium_expires_at=NULL,razorpay_subscription_status=COALESCE(razorpay_subscription_status,'admin_granted') WHERE id=%s AND role='user'""",(user_id,))
            else:
                cur.execute("""UPDATE users SET is_premium=FALSE,premium_expires_at=CURRENT_TIMESTAMP,
                               razorpay_subscription_status='admin_revoked',premium_cancel_at_cycle_end=FALSE WHERE id=%s AND role='user'""",(user_id,))
        conn.commit()
    finally: conn.close()


def delete_managed_user(user_id):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id=%s AND role='user' RETURNING id",(user_id,))
            deleted=cur.fetchone() is not None
        conn.commit(); return deleted
    finally: conn.close()


def add_admin_note(user_id, admin_user_id, note):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO admin_notes(user_id,admin_user_id,note) VALUES(%s,%s,%s)",(user_id,admin_user_id,note.strip()))
        conn.commit()
    finally: conn.close()


def feature_analytics():
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            queries = {
                "transactions":"SELECT COUNT(DISTINCT user_id) FROM transactions",
                "budgets":"SELECT COUNT(DISTINCT user_id) FROM budgets",
                "goals":"SELECT COUNT(DISTINCT user_id) FROM goals",
                "investments":"SELECT COUNT(DISTINCT user_id) FROM investments",
                "watchlist":"SELECT COUNT(DISTINCT user_id) FROM investment_watchlist",
                "bank_accounts":"SELECT COUNT(DISTINCT user_id) FROM financial_accounts",
                "ai":"SELECT COUNT(*) FROM ai_usage WHERE month_requests>0",
            }
            out={}
            for key,q in queries.items(): cur.execute(q); out[key]=int(cur.fetchone()[0] or 0)
            cur.execute("SELECT COUNT(*) FROM users WHERE role='user'"); out["users"]=int(cur.fetchone()[0] or 0)
            cur.execute("SELECT country,COUNT(*) FROM users WHERE role='user' GROUP BY country ORDER BY COUNT(*) DESC LIMIT 12"); out["countries"]=[(r[0] or 'Unknown',int(r[1])) for r in cur.fetchall()]
            cur.execute("SELECT currency,COUNT(*) FROM users WHERE role='user' GROUP BY currency ORDER BY COUNT(*) DESC"); out["currencies"]=[(r[0] or 'Unknown',int(r[1])) for r in cur.fetchall()]
            cur.execute("SELECT user_id,month_requests,day_requests,updated_at FROM ai_usage ORDER BY month_requests DESC LIMIT 20"); out["top_ai"]=[{"user_id":r[0],"month":r[1],"day":r[2],"updated":r[3]} for r in cur.fetchall()]
        return out
    finally: conn.close()


def list_support_messages(limit=200):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,user_id,name,email,issue_type,message,created_at FROM support_messages ORDER BY created_at DESC LIMIT %s",(limit,)); rows=cur.fetchall()
        return [{"id":r[0],"user_id":r[1],"name":r[2],"email":r[3],"issue_type":r[4],"message":r[5],"created_at":r[6]} for r in rows]
    finally: conn.close()


def create_announcement(admin_user_id, title, message, link=None, audience='all', translations=None):
    if audience not in {'all','free','premium'}:
        audience='all'
    translations = translations or {}
    ta = translations.get('ta') or {}
    hi = translations.get('hi') or {}
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO admin_announcements(
                       admin_user_id,title,message,title_ta,message_ta,title_hi,message_hi,link,audience,recipients
                   ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,0) RETURNING id""",
                (admin_user_id,title,message,ta.get('title'),ta.get('message'),hi.get('title'),hi.get('message'),link,audience)
            )
            announcement_id = cur.fetchone()[0]
            cond="role='user' AND account_status='active'"
            if audience=='free':
                cond += " AND is_premium=FALSE"
            elif audience=='premium':
                cond += " AND is_premium=TRUE"
            cur.execute(
                f"""INSERT INTO alerts(user_id,title,message,alert_type,link,fingerprint,announcement_id)
                    SELECT id,%s,%s,'info',%s,%s || '-' || id::text,%s FROM users WHERE {cond}""",
                (title,message,link,f"admin-announcement-{announcement_id}",announcement_id)
            )
            recipients=cur.rowcount
            cur.execute("UPDATE admin_announcements SET recipients=%s WHERE id=%s", (recipients,announcement_id))
        conn.commit(); return recipients
    finally:
        conn.close()


def list_announcements(limit=50):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,title,message,link,audience,recipients,created_at FROM admin_announcements ORDER BY created_at DESC LIMIT %s",(limit,)); rows=cur.fetchall()
        return [{"id":r[0],"title":r[1],"message":r[2],"link":r[3],"audience":r[4],"recipients":r[5],"created_at":r[6]} for r in rows]
    finally: conn.close()


def system_health():
    health={}
    try:
        conn=get_connection();
        with conn.cursor() as cur: cur.execute("SELECT 1"); health['database']=cur.fetchone()[0]==1
        conn.close()
    except Exception:
        health['database']=False
    health['ai_configured']=bool(os.getenv('OPENAI_API_KEY'))
    health['email_configured']=bool(os.getenv('SMTP_HOST') and (os.getenv('SMTP_USER') or os.getenv('SMTP_USERNAME')) and os.getenv('SMTP_PASSWORD'))
    health['razorpay_configured']=bool(os.getenv('RAZORPAY_KEY_ID') and os.getenv('RAZORPAY_KEY_SECRET'))
    health['setu_configured']=bool(os.getenv('SETU_CLIENT_ID') and os.getenv('SETU_CLIENT_SECRET'))
    health['market_data']='Yahoo Finance / public market endpoint'
    health['environment']=os.getenv('RENDER_SERVICE_NAME') or os.getenv('FLASK_ENV') or 'local'
    health['version']=os.getenv('SIGORA_VERSION','launch-ready-2-admin-v1')
    return health

def record_payment_event(event_type, user_id=None, payment_id=None, order_id=None, subscription_id=None,
                         amount=None, currency=None, status=None, source='webhook'):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payment_events(event_type,user_id,payment_id,order_id,subscription_id,amount,currency,status,source)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,(event_type,user_id,payment_id,order_id,subscription_id,amount,currency,status,source))
        conn.commit()
    finally: conn.close()


def list_payment_events(limit=200):
    ensure_admin_schema(); conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,event_type,user_id,payment_id,order_id,subscription_id,amount,currency,status,source,created_at
                           FROM payment_events ORDER BY created_at DESC LIMIT %s""",(limit,)); rows=cur.fetchall()
        return [{"id":r[0],"event_type":r[1],"user_id":r[2],"payment_id":r[3],"order_id":r[4],"subscription_id":r[5],"amount":r[6],"currency":r[7],"status":r[8],"source":r[9],"created_at":r[10]} for r in rows]
    finally: conn.close()
