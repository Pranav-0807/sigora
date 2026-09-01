"""Sigora launch features: settings, gamification, alerts and premium helpers."""

import os
import smtplib
import requests
import secrets
import hashlib
from datetime import date, timedelta, datetime
from email.message import EmailMessage

from database import get_connection
from currency_engine import convert_amount


_SCHEMA_READY = False


def ensure_feature_schema():
    """Create the small set of launch-feature tables/columns if needed."""
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_email_enabled BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS budget_alerts_enabled BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS goal_alerts_enabled BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_alerts_enabled BOOLEAN DEFAULT TRUE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN DEFAULT FALSE")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_started_at TIMESTAMP")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_expires_at TIMESTAMP")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_id VARCHAR(120)")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_status VARCHAR(40)")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_cancel_at_cycle_end BOOLEAN DEFAULT FALSE")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(64) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id, created_at DESC)")
            cur.execute("DELETE FROM password_reset_tokens WHERE expires_at < CURRENT_TIMESTAMP - INTERVAL '1 day'")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR'")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS financial_account_id INTEGER REFERENCES financial_accounts(id) ON DELETE SET NULL")
            cur.execute("ALTER TABLE budgets ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR'")
            cur.execute("ALTER TABLE goals ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR'")
            cur.execute("UPDATE transactions t SET currency=COALESCE(t.currency,u.currency,'INR') FROM users u WHERE u.id=t.user_id AND (t.currency IS NULL OR t.currency='')")
            cur.execute("UPDATE budgets b SET currency=COALESCE(b.currency,u.currency,'INR') FROM users u WHERE u.id=b.user_id AND (b.currency IS NULL OR b.currency='')")
            cur.execute("UPDATE goals g SET currency=COALESCE(g.currency,u.currency,'INR') FROM users u WHERE u.id=g.user_id AND (g.currency IS NULL OR g.currency='')")

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_usage (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    month_start DATE NOT NULL,
                    month_requests INTEGER NOT NULL DEFAULT 0,
                    day_start DATE NOT NULL,
                    day_requests INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_global_usage (
                    month_start DATE PRIMARY KEY,
                    requests INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS support_messages (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    name VARCHAR(100),
                    email VARCHAR(255) NOT NULL,
                    issue_type VARCHAR(80) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS gamification (
                    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                    xp INTEGER NOT NULL DEFAULT 0,
                    level INTEGER NOT NULL DEFAULT 1,
                    current_streak INTEGER NOT NULL DEFAULT 0,
                    best_streak INTEGER NOT NULL DEFAULT 0,
                    last_activity_date DATE,
                    transactions_count INTEGER NOT NULL DEFAULT 0,
                    budgets_created INTEGER NOT NULL DEFAULT 0,
                    goals_created INTEGER NOT NULL DEFAULT 0,
                    goals_completed INTEGER NOT NULL DEFAULT 0,
                    badges TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(180) NOT NULL,
                    message TEXT NOT NULL,
                    alert_type VARCHAR(30) NOT NULL DEFAULT 'info',
                    link VARCHAR(255),
                    fingerprint VARCHAR(255),
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    email_sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS financial_accounts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider VARCHAR(40) NOT NULL,
                    provider_account_id VARCHAR(180),
                    institution_name VARCHAR(180) NOT NULL,
                    account_name VARCHAR(180),
                    account_type VARCHAR(60),
                    country VARCHAR(80) NOT NULL DEFAULT 'India',
                    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                    masked_account VARCHAR(40),
                    balance NUMERIC(18,2),
                    status VARCHAR(30) NOT NULL DEFAULT 'connected',
                    last_synced_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Upgrade older Sigora financial_accounts schemas in-place.
            # CREATE TABLE IF NOT EXISTS does not add missing columns to an existing table.
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS provider VARCHAR(40)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS provider_account_id VARCHAR(180)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS institution_name VARCHAR(180)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS account_name VARCHAR(180)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS account_type VARCHAR(60)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS country VARCHAR(80) DEFAULT 'India'")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR'")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS masked_account VARCHAR(40)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS balance NUMERIC(18,2)")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'connected'")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMP")
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("UPDATE financial_accounts SET provider=COALESCE(provider,'manual'), institution_name=COALESCE(institution_name,'Bank account'), country=COALESCE(country,'India'), currency=COALESCE(currency,'INR'), status=COALESCE(status,'connected')")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_financial_accounts_user ON financial_accounts(user_id)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bank_connections (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    provider VARCHAR(40) NOT NULL,
                    consent_id VARCHAR(180) UNIQUE,
                    data_session_id VARCHAR(180),
                    status VARCHAR(40) NOT NULL DEFAULT 'pending',
                    consent_expires_at TIMESTAMP,
                    last_sync_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Upgrade older bank connection schemas in-place as well.
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS provider VARCHAR(40)")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS consent_id VARCHAR(180)")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS data_session_id VARCHAR(180)")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS status VARCHAR(40) DEFAULT 'pending'")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS consent_expires_at TIMESTAMP")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMP")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("ALTER TABLE bank_connections ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("UPDATE bank_connections SET provider=COALESCE(provider,'setu_aa'), status=COALESCE(status,'pending')")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bank_connections_consent_unique ON bank_connections(consent_id) WHERE consent_id IS NOT NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bank_connections_user ON bank_connections(user_id)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS external_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    financial_account_id INTEGER REFERENCES financial_accounts(id) ON DELETE SET NULL,
                    provider VARCHAR(40) NOT NULL,
                    external_id VARCHAR(240) NOT NULL,
                    transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, provider, external_id)
                )
            """)
            # Upgrade older external transaction schemas in-place.
            cur.execute("ALTER TABLE external_transactions ADD COLUMN IF NOT EXISTS financial_account_id INTEGER REFERENCES financial_accounts(id) ON DELETE SET NULL")
            cur.execute("ALTER TABLE external_transactions ADD COLUMN IF NOT EXISTS provider VARCHAR(40)")
            cur.execute("ALTER TABLE external_transactions ADD COLUMN IF NOT EXISTS external_id VARCHAR(240)")
            cur.execute("ALTER TABLE external_transactions ADD COLUMN IF NOT EXISTS transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL")
            cur.execute("ALTER TABLE external_transactions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_external_transactions_unique ON external_transactions(user_id, provider, external_id) WHERE provider IS NOT NULL AND external_id IS NOT NULL")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_external_transactions_user ON external_transactions(user_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_user_created ON alerts(user_id, created_at DESC)")
            # Older beta builds may have duplicate fingerprints. Keep the newest
            # record before enforcing uniqueness so startup cannot fail here.
            cur.execute("""
                DELETE FROM alerts a
                USING alerts b
                WHERE a.user_id=b.user_id
                  AND a.fingerprint IS NOT NULL
                  AND a.fingerprint=b.fingerprint
                  AND a.id < b.id
            """)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_fingerprint ON alerts(user_id, fingerprint) WHERE fingerprint IS NOT NULL")
        conn.commit()
        _SCHEMA_READY = True
    finally:
        conn.close()


def get_user_settings(user_id):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, email, currency, country,
                       notification_email_enabled, budget_alerts_enabled,
                       goal_alerts_enabled, ai_alerts_enabled, is_premium
                FROM users WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    return {
        "id": row[0], "name": row[1], "email": row[2],
        "currency": row[3] or "INR", "country": row[4] or "India",
        "notification_email_enabled": bool(row[5]),
        "budget_alerts_enabled": bool(row[6]),
        "goal_alerts_enabled": bool(row[7]),
        "ai_alerts_enabled": bool(row[8]),
        "is_premium": bool(row[9]),
    }


def update_user_settings(user_id, name, currency, country,
                         notification_email_enabled, budget_alerts_enabled,
                         goal_alerts_enabled, ai_alerts_enabled):
    ensure_feature_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT currency FROM users WHERE id=%s FOR UPDATE", (user_id,))
            row=cur.fetchone()
            old_currency=(row[0] or "INR").upper() if row else "INR"
            new_currency=(currency or "INR").upper()
            if old_currency != new_currency:
                # Budgets and goals are stored in the user's selected currency.
                # When the user changes currency, re-denominate those stored
                # values using today's FX rate. A goal's target_date is often
                # in the future, so it must never be used as a historical FX
                # lookup date.
                conversion_date = date.today()

                cur.execute("SELECT id,amount,currency FROM budgets WHERE user_id=%s FOR UPDATE", (user_id,))
                budgets=cur.fetchall()
                for bid,amount,curcy in budgets:
                    source = (curcy or old_currency).upper()
                    converted=convert_amount(amount, source, new_currency, conversion_date)
                    cur.execute("UPDATE budgets SET amount=%s,currency=%s WHERE id=%s", (converted,new_currency,bid))

                cur.execute("SELECT id,target_amount,current_amount,currency FROM goals WHERE user_id=%s FOR UPDATE", (user_id,))
                goals=cur.fetchall()
                for gid,target,current,curcy in goals:
                    source=(curcy or old_currency).upper()
                    converted_target=convert_amount(target,source,new_currency,conversion_date)
                    converted_current=convert_amount(current,source,new_currency,conversion_date)
                    cur.execute("UPDATE goals SET target_amount=%s,current_amount=%s,currency=%s WHERE id=%s", (converted_target,converted_current,new_currency,gid))
            cur.execute("UPDATE users SET name=%s,currency=%s,country=%s,notification_email_enabled=%s,budget_alerts_enabled=%s,goal_alerts_enabled=%s,ai_alerts_enabled=%s WHERE id=%s", (name,new_currency,country,notification_email_enabled,budget_alerts_enabled,goal_alerts_enabled,ai_alerts_enabled,user_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def change_user_password(user_id, password_hash):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


def delete_user_account(user_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
    finally:
        conn.close()


def _level_for_xp(xp):
    return max(1, (xp // 100) + 1)


def get_gamification(user_id):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT xp, level, current_streak, best_streak,
                       last_activity_date, transactions_count,
                       budgets_created, goals_created, goals_completed, badges
                FROM gamification WHERE user_id = %s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO gamification (user_id) VALUES (%s)", (user_id,))
                conn.commit()
                return {
                    "xp": 0, "level": 1, "current_streak": 0,
                    "best_streak": 0, "transactions_count": 0,
                    "budgets_created": 0, "goals_created": 0,
                    "goals_completed": 0, "badges": [], "xp_to_next": 100,
                }
    finally:
        conn.close()

    xp = int(row[0])
    return {
        "xp": xp,
        "level": int(row[1]),
        "current_streak": int(row[2]),
        "best_streak": int(row[3]),
        "last_activity_date": str(row[4]) if row[4] else None,
        "transactions_count": int(row[5]),
        "budgets_created": int(row[6]),
        "goals_created": int(row[7]),
        "goals_completed": int(row[8]),
        "badges": list(row[9] or []),
        "xp_to_next": ((int(row[1]) * 100) - xp),
    }


def award_activity(user_id, activity, points=10):
    ensure_feature_schema()
    today = date.today()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT xp, level, current_streak, best_streak, last_activity_date, transactions_count, budgets_created, goals_created, goals_completed, badges FROM gamification WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("INSERT INTO gamification (user_id) VALUES (%s)", (user_id,))
                row = (0, 1, 0, 0, None, 0, 0, 0, 0, [])

            xp, level, streak, best, last_day, tx_count, budget_count, goal_count, completed_count, badges = row
            badges = list(badges or [])
            xp += int(points)

            if last_day is None:
                streak = 1
            elif last_day == today:
                streak = int(streak)
            elif last_day == today - timedelta(days=1):
                streak = int(streak) + 1
            else:
                streak = 1

            best = max(int(best), streak)

            if activity == "transaction":
                tx_count += 1
            elif activity == "budget":
                budget_count += 1
            elif activity == "goal":
                goal_count += 1
            elif activity == "goal_completed":
                completed_count += 1

            if tx_count >= 1 and "first-transaction" not in badges:
                badges.append("first-transaction")
            if tx_count >= 10 and "ten-transactions" not in badges:
                badges.append("ten-transactions")
            if budget_count >= 1 and "budget-builder" not in badges:
                badges.append("budget-builder")
            if goal_count >= 1 and "goal-setter" not in badges:
                badges.append("goal-setter")
            if completed_count >= 1 and "goal-achiever" not in badges:
                badges.append("goal-achiever")
            if streak >= 7 and "seven-day-streak" not in badges:
                badges.append("seven-day-streak")

            level = _level_for_xp(xp)
            cur.execute("""
                UPDATE gamification
                SET xp=%s, level=%s, current_streak=%s, best_streak=%s,
                    last_activity_date=%s, transactions_count=%s,
                    budgets_created=%s, goals_created=%s, goals_completed=%s,
                    badges=%s, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
            """, (xp, level, streak, best, today, tx_count, budget_count,
                  goal_count, completed_count, badges, user_id))
        conn.commit()
    finally:
        conn.close()
    return get_gamification(user_id)


def create_alert(user_id, title, message, alert_type="info", link=None, fingerprint=None):
    """Create/update an alert and attempt email delivery without risking the app.

    Alert failures are deliberately non-fatal: dashboard/login must keep working
    even if email or an old database row is malformed.
    """
    try:
        ensure_feature_schema()
        conn = get_connection()
        alert_id = None
        email_sent_at = None
        user_row = None
        try:
            with conn.cursor() as cur:
                existing = None
                if fingerprint is not None:
                    cur.execute(
                        "SELECT id, email_sent_at FROM alerts WHERE user_id=%s AND fingerprint=%s ORDER BY id DESC LIMIT 1",
                        (user_id, fingerprint),
                    )
                    existing = cur.fetchone()

                if existing:
                    alert_id, email_sent_at = existing
                    # Keep text/link current if wording changes across releases.
                    cur.execute(
                        "UPDATE alerts SET title=%s, message=%s, alert_type=%s, link=%s WHERE id=%s AND user_id=%s",
                        (title, message, alert_type, link, alert_id, user_id),
                    )
                else:
                    cur.execute(
                        """INSERT INTO alerts (user_id,title,message,alert_type,link,fingerprint)
                           VALUES (%s,%s,%s,%s,%s,%s)
                           RETURNING id, email_sent_at""",
                        (user_id, title, message, alert_type, link, fingerprint),
                    )
                    alert_id, email_sent_at = cur.fetchone()

                if alert_id and email_sent_at is None and alert_type in {"warning", "danger", "success"}:
                    cur.execute(
                        "SELECT email, notification_email_enabled FROM users WHERE id=%s",
                        (user_id,),
                    )
                    user_row = cur.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        if user_row and user_row[1]:
            delivered = send_email_alert(
                {"email": user_row[0], "notification_email_enabled": True},
                f"Sigora alert: {title}",
                message,
            )
            if delivered and alert_id:
                conn = get_connection()
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE alerts SET email_sent_at=CURRENT_TIMESTAMP WHERE id=%s AND user_id=%s AND email_sent_at IS NULL",
                            (alert_id, user_id),
                        )
                    conn.commit()
                finally:
                    conn.close()
        return alert_id
    except Exception as exc:
        print(f"Sigora alert creation skipped safely: {exc}")
        return None


def get_alerts(user_id, limit=8):
    try:
        ensure_feature_schema()
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, title, message, alert_type, link, is_read, created_at
                    FROM alerts WHERE user_id=%s
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
                rows = cur.fetchall()
        finally:
            conn.close()
        return [
            {"id": r[0], "title": r[1], "message": r[2], "alert_type": r[3],
             "link": r[4], "is_read": bool(r[5]), "created_at": str(r[6])}
            for r in rows
        ]
    except Exception as exc:
        print(f"Sigora alerts unavailable safely: {exc}")
        return []


def mark_alert_read(user_id, alert_id):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE alerts SET is_read=TRUE WHERE id=%s AND user_id=%s", (alert_id, user_id))
        conn.commit()
    finally:
        conn.close()


def send_transactional_email(recipient, subject, body):
    """Send a transactional Sigora email via Resend, with SMTP fallback."""
    if not recipient:
        return False

    sender = (
        os.getenv("EMAIL_FROM")
        or os.getenv("SMTP_FROM")
        or "no-reply@sigorafinance.com"
    ).strip()
    resend_key = os.getenv("RESEND_API_KEY")
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    if not resend_key and host and host.lower() == "smtp.resend.com":
        resend_key = password

    if resend_key:
        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": f"Sigora <{sender}>",
                    "to": [recipient],
                    "subject": subject,
                    "text": body,
                },
                timeout=12,
            )
            response.raise_for_status()
            return True
        except Exception as exc:
            print(f"Sigora Resend email failed: {exc}")
            return False

    port = int(os.getenv("SMTP_PORT", "587"))
    if not all([host, username, password, sender]):
        print("Sigora email skipped: email provider is not fully configured")
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(message)
        return True
    except Exception as exc:
        print(f"Sigora SMTP email failed: {exc}")
        return False


def send_email_alert(user, subject, body):
    """Deliver an optional user alert by email."""
    if not user.get("notification_email_enabled"):
        return False
    return send_transactional_email(user.get("email"), subject, body)


def create_password_reset_token(user_id, ttl_minutes=30):
    """Create a single-use password reset token with simple abuse throttling."""
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM password_reset_tokens WHERE user_id=%s AND created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'",
                (user_id,),
            )
            if int(cur.fetchone()[0]) >= 5:
                conn.commit()
                return None
            cur.execute(
                "SELECT created_at FROM password_reset_tokens WHERE user_id=%s ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            )
            latest = cur.fetchone()
            if latest and latest[0] and latest[0] > datetime.utcnow() - timedelta(seconds=60):
                conn.commit()
                return None

            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
            cur.execute("UPDATE password_reset_tokens SET used_at=CURRENT_TIMESTAMP WHERE user_id=%s AND used_at IS NULL", (user_id,))
            cur.execute(
                "INSERT INTO password_reset_tokens(user_id, token_hash, expires_at) VALUES(%s,%s,%s)",
                (user_id, token_hash, expires_at),
            )
        conn.commit()
        return token
    finally:
        conn.close()


def password_reset_token_is_valid(token):
    if not token:
        return False
    ensure_feature_schema()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM password_reset_tokens WHERE token_hash=%s AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP",
                (token_hash,),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def reset_password_with_token(token, password_hash):
    """Atomically consume a reset token and replace the user's password."""
    if not token:
        return False
    ensure_feature_schema()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id FROM password_reset_tokens WHERE token_hash=%s AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP FOR UPDATE",
                (token_hash,),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                return False
            reset_id, user_id = row
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (password_hash, user_id))
            cur.execute("UPDATE password_reset_tokens SET used_at=CURRENT_TIMESTAMP WHERE id=%s", (reset_id,))
            cur.execute("UPDATE password_reset_tokens SET used_at=CURRENT_TIMESTAMP WHERE user_id=%s AND used_at IS NULL", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def premium_features(intelligence=None):
    features = [
        ("Predictive Risk Engine", "Detect likely budget breaches before month-end and calculate a practical daily correction."),
        ("Financial Health Score", "An explainable 0–100 score across savings, budgets, goals and cash-flow stability."),
        ("What-if Simulator", "Model a planned purchase against your recorded savings and goals before you spend."),
        ("Advanced AI Insights", "AI explanations grounded in Sigora's deterministic financial signals."),
        ("Advanced Reports", "Deeper spending, trend and cash-flow analysis."),
        ("Advanced Goal Intelligence", "Connect spending decisions with the goals they can accelerate or delay."),
        ("30 AI analyses / month", "A larger AI allowance with built-in platform safety limits."),
    ]
    if intelligence and intelligence.get("risks"):
        features[0] = ("Predictive Risk Engine", f"{len(intelligence['risks'])} current budget risk(s) detected from your recorded pace.")
    return features


def sync_financial_alerts(user_id, budgets=None, goals=None):
    """Keep active financial alerts in sync with the user's current data."""
    ensure_feature_schema()
    settings = get_user_settings(user_id)
    if not settings:
        return

    today = date.today()
    symbol = COUNTRY_CURRENCIES.get(
        settings.get("country"),
        (settings.get("currency", "INR"), "₹")
    )[1]

    active_budget_fingerprints = []
    if budgets is not None and settings["budget_alerts_enabled"]:
        for budget in budgets:
            amount = float(budget.get("amount", 0) or 0)
            spent = float(budget.get("spent", 0) or 0)
            if amount <= 0:
                continue
            ratio = spent / amount
            if ratio >= 1:
                fingerprint = f"budget-over-{budget['id']}-{budget['year']}-{budget['month']}"
                active_budget_fingerprints.append(fingerprint)
                create_alert(
                    user_id,
                    f"{budget['category']} budget exceeded",
                    f"You've spent {symbol}{spent:,.0f} against a {symbol}{amount:,.0f} budget.",
                    "danger", "/budgets", fingerprint
                )
            elif ratio >= 0.8:
                fingerprint = f"budget-80-{budget['id']}-{budget['year']}-{budget['month']}"
                active_budget_fingerprints.append(fingerprint)
                create_alert(
                    user_id,
                    f"{budget['category']} budget is nearly used",
                    f"You've used {ratio * 100:.0f}% of this month's budget.",
                    "warning", "/budgets", fingerprint
                )

    active_goal_fingerprints = []
    if goals is not None and settings["goal_alerts_enabled"]:
        for goal in goals:
            target = float(goal.get("target_amount", 0) or 0)
            current = float(goal.get("current_amount", 0) or 0)
            if target <= 0:
                continue
            if current >= target:
                fingerprint = f"goal-complete-{goal['id']}"
                active_goal_fingerprints.append(fingerprint)
                create_alert(
                    user_id,
                    f"Goal completed: {goal['name']}",
                    "You reached this goal. Nice work!",
                    "success", "/goals", fingerprint
                )
                continue
            try:
                target_date = date.fromisoformat(str(goal["target_date"]))
            except ValueError:
                continue
            days = (target_date - today).days
            if 0 <= days <= 7:
                fingerprint = f"goal-deadline-{goal['id']}-{target_date}"
                active_goal_fingerprints.append(fingerprint)
                create_alert(
                    user_id,
                    f"Goal deadline approaching: {goal['name']}",
                    f"Your target date is in {days} day(s).",
                    "warning", "/goals", fingerprint
                )

    # Remove stale financial alerts that no longer correspond to an active
    # budget/goal condition. This also cleans records left by older builds.
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if budgets is not None:
                if active_budget_fingerprints:
                    placeholders = ",".join(["%s"] * len(active_budget_fingerprints))
                    cur.execute(
                        f"""DELETE FROM alerts
                            WHERE user_id=%s
                              AND (link='/budgets' OR fingerprint LIKE 'budget-%%')
                              AND (fingerprint IS NULL OR fingerprint NOT IN ({placeholders}))""",
                        [user_id] + active_budget_fingerprints
                    )
                else:
                    cur.execute(
                        "DELETE FROM alerts WHERE user_id=%s AND (link='/budgets' OR fingerprint LIKE 'budget-%%')",
                        (user_id,)
                    )
            if goals is not None:
                if active_goal_fingerprints:
                    placeholders = ",".join(["%s"] * len(active_goal_fingerprints))
                    cur.execute(
                        f"""DELETE FROM alerts
                            WHERE user_id=%s
                              AND (link='/goals' OR fingerprint LIKE 'goal-complete-%%' OR fingerprint LIKE 'goal-deadline-%%')
                              AND (fingerprint IS NULL OR fingerprint NOT IN ({placeholders}))""",
                        [user_id] + active_goal_fingerprints
                    )
                else:
                    cur.execute(
                        "DELETE FROM alerts WHERE user_id=%s AND (link='/goals' OR fingerprint LIKE 'goal-complete-%%' OR fingerprint LIKE 'goal-deadline-%%')",
                        (user_id,)
                    )
        conn.commit()
    finally:
        conn.close()


# =====================================================
# AI USAGE / PREMIUM SAFETY
# =====================================================

FREE_AI_MONTHLY_LIMIT = int(os.getenv("FREE_AI_MONTHLY_LIMIT", "5"))
PREMIUM_AI_MONTHLY_LIMIT = int(os.getenv("PREMIUM_AI_MONTHLY_LIMIT", "30"))
FREE_AI_DAILY_LIMIT = int(os.getenv("FREE_AI_DAILY_LIMIT", "2"))
PREMIUM_AI_DAILY_LIMIT = int(os.getenv("PREMIUM_AI_DAILY_LIMIT", "5"))
AI_MONTHLY_BUDGET_USD = float(os.getenv("AI_MONTHLY_BUDGET_USD", "5"))
AI_ESTIMATED_COST_PER_REQUEST_USD = float(os.getenv("AI_ESTIMATED_COST_PER_REQUEST_USD", "0.01"))
AI_GLOBAL_MONTHLY_REQUEST_LIMIT = int(os.getenv("AI_GLOBAL_MONTHLY_REQUEST_LIMIT", "2000"))


def get_ai_limits(is_premium=False):
    return {
        "monthly": PREMIUM_AI_MONTHLY_LIMIT if is_premium else FREE_AI_MONTHLY_LIMIT,
        "daily": PREMIUM_AI_DAILY_LIMIT if is_premium else FREE_AI_DAILY_LIMIT,
        "global_monthly": AI_GLOBAL_MONTHLY_REQUEST_LIMIT,
    }


def get_ai_usage(user_id):
    ensure_feature_schema()
    today = date.today()
    month_start = today.replace(day=1)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT month_start, month_requests, day_start, day_requests
                FROM ai_usage WHERE user_id=%s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                cur.execute("""
                    INSERT INTO ai_usage(user_id, month_start, month_requests, day_start, day_requests)
                    VALUES(%s,%s,0,%s,0)
                """, (user_id, month_start, today))
                conn.commit()
                return {"month_requests": 0, "day_requests": 0}
            stored_month, month_requests, stored_day, day_requests = row
            if stored_month != month_start:
                month_requests = 0
            if stored_day != today:
                day_requests = 0
            return {"month_requests": int(month_requests), "day_requests": int(day_requests)}
    finally:
        conn.close()


def consume_ai_request(user_id, is_premium=False):
    """Atomically reserve one AI request with per-user and app-wide guardrails."""
    ensure_feature_schema()
    today = date.today()
    month_start = today.replace(day=1)
    limits = get_ai_limits(is_premium)
    monthly_limit = limits["monthly"]
    daily_limit = limits["daily"]
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ai_usage(user_id, month_start, month_requests, day_start, day_requests)
                VALUES(%s,%s,0,%s,0)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, month_start, today))
            cur.execute("""
                INSERT INTO ai_global_usage(month_start, requests) VALUES(%s,0)
                ON CONFLICT (month_start) DO NOTHING
            """, (month_start,))
            cur.execute("SELECT requests FROM ai_global_usage WHERE month_start=%s FOR UPDATE", (month_start,))
            global_requests = int(cur.fetchone()[0])
            if AI_GLOBAL_MONTHLY_REQUEST_LIMIT > 0 and global_requests >= AI_GLOBAL_MONTHLY_REQUEST_LIMIT:
                conn.commit()
                return {"allowed": False, "reason": "global", "used": 0, "limit": monthly_limit, "daily_used": 0, "daily_limit": daily_limit}

            cur.execute("""
                SELECT month_start, month_requests, day_start, day_requests
                FROM ai_usage WHERE user_id=%s FOR UPDATE
            """, (user_id,))
            month, month_requests, day, day_requests = cur.fetchone()
            if month != month_start:
                month_requests = 0
                month = month_start
            if day != today:
                day_requests = 0
                day = today

            # Per-user cost guardrail; this is intentionally independent of Google billing.
            estimated_spend = float(month_requests) * AI_ESTIMATED_COST_PER_REQUEST_USD
            if AI_MONTHLY_BUDGET_USD > 0 and estimated_spend + AI_ESTIMATED_COST_PER_REQUEST_USD > AI_MONTHLY_BUDGET_USD:
                conn.commit()
                return {"allowed": False, "reason": "budget", "used": int(month_requests), "limit": monthly_limit, "daily_used": int(day_requests), "daily_limit": daily_limit}
            if month_requests >= monthly_limit:
                conn.commit()
                return {"allowed": False, "reason": "monthly", "used": int(month_requests), "limit": monthly_limit, "daily_used": int(day_requests), "daily_limit": daily_limit}
            if day_requests >= daily_limit:
                conn.commit()
                return {"allowed": False, "reason": "daily", "used": int(month_requests), "limit": monthly_limit, "daily_used": int(day_requests), "daily_limit": daily_limit}

            month_requests += 1
            day_requests += 1
            cur.execute("""
                UPDATE ai_usage SET month_start=%s, month_requests=%s, day_start=%s, day_requests=%s, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
            """, (month, month_requests, day, day_requests, user_id))
            cur.execute("UPDATE ai_global_usage SET requests=requests+1, updated_at=CURRENT_TIMESTAMP WHERE month_start=%s", (month_start,))
        conn.commit()
        return {"allowed": True, "reason": None, "used": int(month_requests), "limit": monthly_limit, "daily_used": int(day_requests), "daily_limit": daily_limit}
    finally:
        conn.close()


def get_premium_status(user_id):
    """Return the authoritative entitlement; expired access is cleaned up in the DB."""
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT is_premium, premium_started_at, premium_expires_at,
                                  razorpay_subscription_id, razorpay_subscription_status,
                                  premium_cancel_at_cycle_end
                           FROM users WHERE id=%s""", (user_id,))
            row = cur.fetchone()
            if not row:
                return {"is_premium": False, "started_at": None, "expires_at": None, "subscription_id": None, "subscription_status": None, "cancel_at_cycle_end": False}
            active = bool(row[0])
            expires_at = row[2]
            if active and expires_at is not None:
                try:
                    now = datetime.now(expires_at.tzinfo) if getattr(expires_at, "tzinfo", None) else datetime.now()
                    if expires_at < now:
                        active = False
                        cur.execute("UPDATE users SET is_premium=FALSE WHERE id=%s", (user_id,))
                        conn.commit()
                except Exception:
                    pass
            return {
                "is_premium": active, "started_at": row[1], "expires_at": expires_at,
                "subscription_id": row[3], "subscription_status": row[4],
                "cancel_at_cycle_end": bool(row[5]),
            }
    finally:
        conn.close()


def set_premium_status(user_id, active, expires_at=None, subscription_status=None):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if active:
                cur.execute("""UPDATE users SET is_premium=TRUE,
                               premium_started_at=COALESCE(premium_started_at, CURRENT_TIMESTAMP),
                               premium_expires_at=%s,
                               razorpay_subscription_status=COALESCE(%s, razorpay_subscription_status)
                               WHERE id=%s""", (expires_at, subscription_status, user_id))
            else:
                cur.execute("""UPDATE users SET is_premium=FALSE, premium_expires_at=%s,
                               razorpay_subscription_status=COALESCE(%s, razorpay_subscription_status),
                               premium_cancel_at_cycle_end=FALSE
                               WHERE id=%s""", (expires_at, subscription_status, user_id))
        conn.commit()
    finally:
        conn.close()


def mark_subscription_cancellation_requested(user_id, requested=True):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET premium_cancel_at_cycle_end=%s WHERE id=%s", (bool(requested), user_id))
        conn.commit()
    finally:
        conn.close()


# =====================================================
# SUPPORT
# =====================================================

def submit_support_message(user_id, name, email, issue_type, message):
    ensure_feature_schema()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO support_messages(user_id, name, email, issue_type, message)
                VALUES(%s,%s,%s,%s,%s)
            """, (user_id, name, email, issue_type, message))
        conn.commit()
    finally:
        conn.close()

    support_email = os.getenv("SIGORA_SUPPORT_EMAIL")
    if support_email:
        send_email_alert(
            {"email": support_email, "notification_email_enabled": True},
            f"Sigora support request: {issue_type}",
            f"From: {name} <{email}>\n\n{message}"
        )


# =====================================================
# CONFIGURABLE MONETIZATION / CURRENCY
# =====================================================
COUNTRY_CURRENCIES = {
    "India": ("INR", "₹"), "United States": ("USD", "$"), "United Kingdom": ("GBP", "£"),
    "Canada": ("CAD", "C$"), "Australia": ("AUD", "A$"), "Germany": ("EUR", "€"),
    "France": ("EUR", "€"), "Spain": ("EUR", "€"), "Italy": ("EUR", "€"),
    "Netherlands": ("EUR", "€"), "Switzerland": ("CHF", "CHF"), "Portugal": ("EUR", "€"),
    "Ireland": ("EUR", "€"), "Singapore": ("SGD", "S$"), "United Arab Emirates": ("AED", "د.إ"),
    "Japan": ("JPY", "¥"), "New Zealand": ("NZD", "NZ$"), "South Africa": ("ZAR", "R"),
}
COUNTRIES = sorted(COUNTRY_CURRENCIES.keys())
PREMIUM_PRICE = float(os.getenv("PREMIUM_PRICE", "149"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()

# Fixed regional prices are intentional: billing should not change every day with FX.
# Each currency can be overridden from Render without a code deploy.
REGIONAL_PREMIUM_PRICES = {
    "INR": (149, "₹"), "USD": (1.99, "$"), "EUR": (1.99, "€"), "GBP": (1.49, "£"),
    "CAD": (2.99, "C$"), "AUD": (2.99, "A$"), "CHF": (1.99, "CHF "), "SGD": (2.99, "S$"),
    "AED": (7.99, "د.إ "), "JPY": (299, "¥"), "NZD": (3.49, "NZ$"), "ZAR": (39, "R"),
}

def get_pricing(currency="INR", country=None):
    currency = (currency or currency_for_country(country)[0] or "INR").upper()
    default_amount, symbol = REGIONAL_PREMIUM_PRICES.get(currency, REGIONAL_PREMIUM_PRICES["INR"])
    amount = float(os.getenv(f"SIGORA_PREMIUM_PRICE_{currency}", str(default_amount)))
    plan_env = "RAZORPAY_PLAN_ID" if currency == "INR" else f"RAZORPAY_PLAN_ID_{currency}"
    plan_id = os.getenv(plan_env, "").strip()
    return {"premium_price": amount, "currency": currency, "currency_symbol": symbol, "plan_id": plan_id, "plan_env": plan_env}

def currency_for_country(country):
    return COUNTRY_CURRENCIES.get(country, ("INR","₹"))

def ensure_monetization_schema():
    ensure_feature_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS coupons (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(60) UNIQUE NOT NULL,
                    discount_type VARCHAR(20) NOT NULL DEFAULT 'percent',
                    discount_value NUMERIC(10,2) NOT NULL,
                    max_uses INTEGER,
                    uses INTEGER NOT NULL DEFAULT 0,
                    valid_from TIMESTAMP,
                    valid_until TIMESTAMP,
                    active BOOLEAN NOT NULL DEFAULT TRUE,
                    first_month_only BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("ALTER TABLE coupons ADD COLUMN IF NOT EXISTS razorpay_offer_id VARCHAR(120)")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS subscription_coupons (
                    subscription_id VARCHAR(120) PRIMARY KEY,
                    coupon_id INTEGER REFERENCES coupons(id) ON DELETE SET NULL,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    redeemed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS coupon_redemptions (
                    coupon_id INTEGER REFERENCES coupons(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(coupon_id,user_id)
                )
            """)
        conn.commit()
    finally:
        conn.close()

def list_coupons():
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,code,discount_type,discount_value,max_uses,uses,valid_from,valid_until,active,first_month_only,razorpay_offer_id FROM coupons ORDER BY created_at DESC")
            return cur.fetchall()
    finally: conn.close()

def create_coupon(code, discount_type, discount_value, max_uses=None, valid_until=None, first_month_only=False, razorpay_offer_id=None):
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO coupons(code,discount_type,discount_value,max_uses,valid_until,first_month_only,razorpay_offer_id)
                           VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                        (code.strip().upper(),discount_type,discount_value,max_uses,valid_until,first_month_only,razorpay_offer_id))
            cid=cur.fetchone()[0]
        conn.commit(); return cid
    finally: conn.close()

def toggle_coupon(coupon_id, active):
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur: cur.execute("UPDATE coupons SET active=%s WHERE id=%s",(active,coupon_id))
        conn.commit()
    finally: conn.close()

def validate_coupon(code, user_id):
    ensure_monetization_schema()
    if not code: return {"valid":False,"message":"Enter a coupon code."}
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,code,discount_type,discount_value,max_uses,uses,valid_from,valid_until,active,first_month_only,razorpay_offer_id FROM coupons WHERE code=%s",(code.strip().upper(),))
            row=cur.fetchone()
            if not row: return {"valid":False,"message":"Coupon not found."}
            cid,code,typ,val,maxu,uses,vf,vu,active,first,offer_id=row
            from datetime import datetime
            now=datetime.utcnow()
            if not active or (vf and now<vf) or (vu and now>vu) or (maxu is not None and uses>=maxu):
                return {"valid":False,"message":"Coupon is expired or unavailable."}
            cur.execute("SELECT 1 FROM coupon_redemptions WHERE coupon_id=%s AND user_id=%s",(cid,user_id))
            if cur.fetchone(): return {"valid":False,"message":"Coupon already used on this account."}
            # A Sigora coupon changes the actual recurring charge only through a Razorpay Offer.
            if not offer_id:
                return {"valid":False,"message":"This coupon is not linked to a Razorpay Offer yet."}
            if maxu is not None:
                cur.execute("""SELECT COUNT(*) FROM subscription_coupons
                               WHERE coupon_id=%s AND redeemed=FALSE AND created_at >= CURRENT_TIMESTAMP - INTERVAL '30 minutes'""", (cid,))
                reserved = int(cur.fetchone()[0])
                if uses + reserved >= maxu:
                    return {"valid":False,"message":"Coupon is currently fully reserved. Please try again shortly."}
            return {"valid":True,"id":cid,"code":code,"discount_type":typ,"discount_value":float(val),"first_month_only":first,"razorpay_offer_id":offer_id}
    finally: conn.close()

def redeem_coupon(coupon_id,user_id):
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO coupon_redemptions(coupon_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(coupon_id,user_id))
            if cur.rowcount:
                cur.execute("UPDATE coupons SET uses=uses+1 WHERE id=%s",(coupon_id,))
        conn.commit()
    finally: conn.close()


def remember_subscription_coupon(subscription_id, coupon_id, user_id):
    """Remember a coupon selection without consuming it before payment succeeds."""
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO subscription_coupons(subscription_id,coupon_id,user_id)
                           VALUES(%s,%s,%s)
                           ON CONFLICT(subscription_id) DO UPDATE SET coupon_id=EXCLUDED.coupon_id,user_id=EXCLUDED.user_id""",
                        (subscription_id,coupon_id,user_id))
        conn.commit()
    finally: conn.close()

def redeem_subscription_coupon(subscription_id):
    """Consume a pending coupon only after Razorpay confirms activation/payment."""
    ensure_monetization_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT coupon_id,user_id,redeemed FROM subscription_coupons WHERE subscription_id=%s FOR UPDATE",(subscription_id,))
            row=cur.fetchone()
            if not row or row[2] or row[0] is None:
                conn.commit(); return False
            coupon_id,user_id,_=row
            cur.execute("SELECT max_uses,uses,active,valid_until FROM coupons WHERE id=%s FOR UPDATE", (coupon_id,))
            coupon=cur.fetchone()
            if not coupon:
                conn.commit(); return False
            max_uses,uses,active,valid_until=coupon
            now=datetime.utcnow()
            if (not active) or (valid_until and now>valid_until) or (max_uses is not None and uses>=max_uses):
                conn.commit(); return False
            cur.execute("INSERT INTO coupon_redemptions(coupon_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(coupon_id,user_id))
            if cur.rowcount:
                cur.execute("UPDATE coupons SET uses=uses+1 WHERE id=%s",(coupon_id,))
            cur.execute("UPDATE subscription_coupons SET redeemed=TRUE WHERE subscription_id=%s",(subscription_id,))
        conn.commit(); return True
    finally: conn.close()


def get_user_id_for_subscription(subscription_id):
    ensure_feature_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE razorpay_subscription_id=%s",(subscription_id,))
            row=cur.fetchone()
            return row[0] if row else None
    finally: conn.close()


def get_razorpay_subscription_id(user_id):
    ensure_feature_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT razorpay_subscription_id FROM users WHERE id=%s",(user_id,))
            row=cur.fetchone()
            return row[0] if row else None
    finally: conn.close()
