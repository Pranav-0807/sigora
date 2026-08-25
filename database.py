import os

import psycopg
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from currency_engine import convert_amount


# =====================================================
# ENVIRONMENT
# =====================================================

load_dotenv()


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "dbname=sigora"
)


# =====================================================
# DATABASE CONNECTION
# =====================================================

def get_connection():

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured."
        )

    return psycopg.connect(DATABASE_URL)


# =====================================================
# TRANSACTIONS
# =====================================================

def get_transactions(user_id):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id,transaction_type,amount,currency,category,description,date,source,created_at FROM transactions WHERE user_id=%s ORDER BY date DESC,id DESC",(user_id,)); rows=cur.fetchall()
    conn.close()
    return [{"id":r[0],"transaction_type":r[1],"amount":float(r[2]),"currency":r[3] or "INR","category":r[4],"description":r[5],"date":str(r[6]),"source":r[7],"created_at":str(r[8])} for r in rows]


def delete_transaction(user_id, transaction_id):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            DELETE FROM transactions
            WHERE id = %s
              AND user_id = %s
            """,
            (
                transaction_id,
                user_id
            )
        )

    conn.commit()
    conn.close()


def get_transaction(user_id,transaction_id):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id,transaction_type,amount,currency,category,description,date,source,created_at FROM transactions WHERE id=%s AND user_id=%s",(transaction_id,user_id)); r=cur.fetchone()
    conn.close()
    if r is None: return None
    return {"id":r[0],"transaction_type":r[1],"amount":float(r[2]),"currency":r[3] or "INR","category":r[4],"description":r[5],"date":str(r[6]),"source":r[7],"created_at":str(r[8])}


def update_transaction(
    user_id,
    transaction_id,
    transaction_type,
    amount,
    category,
    description,
    date
):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE transactions
            SET transaction_type = %s,
                amount = %s,
                category = %s,
                description = %s,
                date = %s
            WHERE id = %s
              AND user_id = %s
            """,
            (
                transaction_type,
                amount,
                category,
                description,
                date,
                transaction_id,
                user_id
            )
        )

    conn.commit()
    conn.close()


def add_transaction(user_id, transaction_type, amount, category, description, date, source="manual", currency=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if not currency:
                cur.execute("SELECT currency FROM users WHERE id=%s", (user_id,)); row=cur.fetchone(); currency=(row[0] if row else "INR") or "INR"
            cur.execute("""INSERT INTO transactions (user_id,transaction_type,amount,currency,category,description,date,source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", (user_id,transaction_type,amount,currency,category,description,date,source))
            tid=cur.fetchone()[0]
        conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


# =====================================================
# USERS / AUTHENTICATION
# =====================================================

def create_user(
    name,
    email,
    password,
    currency="INR",
    country="India"
):

    conn = get_connection()

    password_hash = generate_password_hash(
        password,
        method="pbkdf2:sha256"
    )

    try:

        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    currency,
                    country
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    name,
                    email,
                    password_hash,
                    currency,
                    country
                )
            )

            user_id = cur.fetchone()[0]

        conn.commit()

        return user_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


def get_user_by_email(email):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id,
                   name,
                   email,
                   password_hash,
                   currency,
                   country
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "password_hash": row[3],
        "currency": row[4],
        "country": row[5]
    }


def get_user_by_id(user_id):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT id,
                   name,
                   email,
                   password_hash,
                   currency,
                   country
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        row = cur.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "email": row[2],
        "password_hash": row[3],
        "currency": row[4],
        "country": row[5]
    }


def check_user_password(password, password_hash):

    return check_password_hash(
        password_hash,
        password
    )


# =====================================================
# GOALS
# =====================================================

def get_goals(user_id):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id,name,target_amount,current_amount,currency,target_date,created_at FROM goals WHERE user_id=%s ORDER BY target_date ASC,id ASC", (user_id,)); rows=cur.fetchall()
    conn.close()
    return [{"id":r[0],"name":r[1],"target_amount":float(r[2]),"current_amount":float(r[3]),"currency":r[4] or "INR","target_date":str(r[5]),"created_at":str(r[6])} for r in rows]


def add_goal(user_id,name,target_amount,current_amount,target_date,currency=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if not currency:
                cur.execute("SELECT currency FROM users WHERE id=%s",(user_id,)); row=cur.fetchone(); currency=(row[0] if row else "INR") or "INR"
            cur.execute("SELECT id FROM goals WHERE user_id=%s AND LOWER(name)=LOWER(%s) AND target_date=%s AND target_amount=%s",(user_id,name,target_date,target_amount))
            if cur.fetchone(): conn.rollback(); return None
            cur.execute("INSERT INTO goals (user_id,name,target_amount,current_amount,currency,target_date) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",(user_id,name.strip(),target_amount,current_amount,currency,target_date))
            gid=cur.fetchone()[0]
        conn.commit(); return gid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def delete_goal(user_id, goal_id):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            DELETE FROM goals
            WHERE id = %s
              AND user_id = %s
            """,
            (
                goal_id,
                user_id
            )
        )
        # Remove dashboard alerts that belonged to the deleted goal.
        cur.execute(
            """
            DELETE FROM alerts
            WHERE user_id = %s
              AND (fingerprint = %s OR fingerprint LIKE %s)
            """,
            (
                user_id,
                f"goal-complete-{goal_id}",
                f"goal-deadline-{goal_id}-%"
            )
        )

    conn.commit()
    conn.close()


def update_goal(user_id,goal_id,name,target_amount,current_amount,target_date,currency=None):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            UPDATE goals
            SET name = %s, target_amount = %s, current_amount = %s, currency = COALESCE(%s,currency), target_date = %s
            WHERE id = %s
              AND user_id = %s
            """,
            (
                name,
                target_amount, current_amount, currency, target_date, goal_id,
                user_id
            )
        )

    conn.commit()
    conn.close()


# =====================================================
# BUDGETS
# =====================================================

def get_budgets(user_id,month,year):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id,category,amount,currency,month,year,created_at FROM budgets WHERE user_id=%s AND month=%s AND year=%s ORDER BY category ASC,id ASC",(user_id,month,year)); rows=cur.fetchall()
    conn.close()
    return [{"id":r[0],"category":r[1],"amount":float(r[2]),"currency":r[3] or "INR","month":r[4],"year":r[5],"created_at":str(r[6])} for r in rows]


def add_budget(user_id,category,amount,month,year,currency=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if not currency:
                cur.execute("SELECT currency FROM users WHERE id=%s",(user_id,)); row=cur.fetchone(); currency=(row[0] if row else "INR") or "INR"
            cur.execute("SELECT id FROM budgets WHERE user_id=%s AND LOWER(category)=LOWER(%s) AND month=%s AND year=%s",(user_id,category,month,year))
            if cur.fetchone(): conn.rollback(); return None
            cur.execute("INSERT INTO budgets (user_id,category,amount,currency,month,year) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",(user_id,category.strip().title(),amount,currency,month,year)); bid=cur.fetchone()[0]
        conn.commit(); return bid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def delete_budget(user_id, budget_id):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute(
            """
            DELETE FROM budgets
            WHERE id = %s
              AND user_id = %s
            """,
            (
                budget_id,
                user_id
            )
        )
        # Remove dashboard alerts that belonged to the deleted budget.
        cur.execute(
            """
            DELETE FROM alerts
            WHERE user_id = %s
              AND (fingerprint LIKE %s OR fingerprint LIKE %s)
            """,
            (
                user_id,
                f"budget-80-{budget_id}-%",
                f"budget-over-{budget_id}-%"
            )
        )

    conn.commit()
    conn.close()


def update_budget(user_id,budget_id,category,amount,month,year,currency=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE budgets SET category=%s,amount=%s,currency=COALESCE(%s,currency),month=%s,year=%s WHERE id=%s AND user_id=%s",(category,amount,currency,month,year,budget_id,user_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def get_budget_spending(user_id,category,month,year):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT amount,currency,date FROM transactions WHERE user_id=%s AND LOWER(category)=LOWER(%s) AND transaction_type='expense' AND EXTRACT(MONTH FROM date)=%s AND EXTRACT(YEAR FROM date)=%s",(user_id,category,month,year)); rows=cur.fetchall()
        cur.execute("SELECT currency FROM users WHERE id=%s",(user_id,)); row=cur.fetchone(); target=(row[0] if row else "INR") or "INR"
    conn.close()
    return sum(convert_amount(r[0],r[1] or target,target,r[2]) for r in rows)


# =====================================================
# MONTHLY SAVINGS
# =====================================================

def _user_tx_rows(user_id):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT transaction_type,amount,currency,date,category FROM transactions WHERE user_id=%s",(user_id,)); rows=cur.fetchall()
        cur.execute("SELECT currency FROM users WHERE id=%s",(user_id,)); row=cur.fetchone(); target=(row[0] if row else "INR") or "INR"
    conn.close()
    return rows,target

def get_monthly_savings(user_id):
    rows,target=_user_tx_rows(user_id); buckets={}
    for typ,amount,curcy,dt,cat in rows:
        key=(dt.year,dt.month); buckets.setdefault(key,[0.0,0.0]); val=convert_amount(amount,curcy or target,target,dt)
        buckets[key][0 if str(typ).lower()=="income" else 1]+=val
    return [{"month":f"{y:04d}-{m:02d}-01","income":round(v[0],2),"expenses":round(v[1],2),"savings":round(v[0]-v[1],2)} for (y,m),v in sorted(buckets.items(),reverse=True)[:6]]


# =====================================================
# REPORTS
# =====================================================

def get_report_totals(user_id):
    rows,target=_user_tx_rows(user_id); income=expense=0.0
    for typ,amount,curcy,dt,cat in rows:
        val=convert_amount(amount,curcy or target,target,dt)
        if str(typ).lower()=="income": income+=val
        elif str(typ).lower()=="expense": expense+=val
    return {"total_income":round(income,2),"total_expense":round(expense,2)}


def get_monthly_report(user_id):
    rows,target=_user_tx_rows(user_id); buckets={}
    for typ,amount,curcy,dt,cat in rows:
        key=(dt.year,dt.month); buckets.setdefault(key,[0.0,0.0]); val=convert_amount(amount,curcy or target,target,dt)
        buckets[key][0 if str(typ).lower()=="income" else 1]+=val
    return [{"year":y,"month":m,"income":round(v[0],2),"expense":round(v[1],2)} for (y,m),v in sorted(buckets.items())]


def get_expense_categories(user_id):
    rows,target=_user_tx_rows(user_id); totals={}
    for typ,amount,curcy,dt,cat in rows:
        if str(typ).lower()!="expense": continue
        key=(cat or "Other").strip().title(); totals[key]=totals.get(key,0)+convert_amount(amount,curcy or target,target,dt)
    return [{"category":k,"total":round(v,2)} for k,v in sorted(totals.items(),key=lambda x:x[1],reverse=True)]


def get_expense_categories_by_period(user_id):
    rows,target=_user_tx_rows(user_id); out={}
    for typ,amount,curcy,dt,cat in rows:
        if str(typ).lower()!="expense": continue
        key=(dt.year,dt.month,(cat or "Other").strip().title()); out[key]=out.get(key,0)+convert_amount(amount,curcy or target,target,dt)
    return [{"year":y,"month":m,"category":c,"total":round(v,2)} for (y,m,c),v in sorted(out.items())]


def get_ai_financial_context(user_id):

    # ==========================================
    # EXISTING FINANCIAL DATA
    # ==========================================

    report = get_report_totals(user_id)

    monthly_report = get_monthly_report(
        user_id
    )

    category_report = get_expense_categories_by_period(
        user_id
    )

    # ==========================================
    # OVERALL FINANCIAL POSITION
    # ==========================================

    total_income = report["total_income"]

    total_expense = report["total_expense"]

    savings = (
        total_income
        - total_expense
    )

    if total_income > 0:

        savings_rate = (
            savings
            / total_income
        ) * 100

    else:

        savings_rate = 0

    # ==========================================
    # LATEST + PREVIOUS MONTH
    # ==========================================

    latest_month = None

    previous_month = None

    if monthly_report:

        latest_month = monthly_report[-1]

    if len(monthly_report) >= 2:

        previous_month = monthly_report[-2]

    # ==========================================
    # MONTH-OVER-MONTH CHANGES
    # ==========================================

    expense_change = None

    income_change = None

    if latest_month and previous_month:

        previous_expense = (
            previous_month["expense"]
        )

        current_expense = (
            latest_month["expense"]
        )

        previous_income = (
            previous_month["income"]
        )

        current_income = (
            latest_month["income"]
        )

        if previous_expense > 0:

            expense_change = (
                (
                    current_expense
                    - previous_expense
                )
                / previous_expense
            ) * 100

        if previous_income > 0:

            income_change = (
                (
                    current_income
                    - previous_income
                )
                / previous_income
            ) * 100

    # ==========================================
    # LATEST MONTH CATEGORIES
    # ==========================================

    latest_categories = []

    if latest_month:

        for item in category_report:

            if (
                item["year"]
                == latest_month["year"]
                and
                item["month"]
                == latest_month["month"]
            ):

                latest_categories.append(
                    {
                        "category": item["category"],
                        "total": item["total"]
                    }
                )

    # ==========================================
    # TOP EXPENSE CATEGORY
    # ==========================================

    top_category = None

    if latest_categories:

        top_category = max(
            latest_categories,
            key=lambda x: x["total"]
        )

    # ==========================================
    # LARGEST EXPENSE CATEGORY SHARE
    # ==========================================

    top_category_percentage = None

    if (
        top_category
        and latest_month
        and latest_month["expense"] > 0
    ):

        top_category_percentage = (
            top_category["total"]
            / latest_month["expense"]
        ) * 100

    # ==========================================
    # MONTHLY SAVINGS HISTORY
    # ==========================================

    monthly_savings = []

    for month in monthly_report:

        month_savings = (
            month["income"]
            - month["expense"]
        )

        if month["income"] > 0:

            month_savings_rate = (
                month_savings
                / month["income"]
            ) * 100

        else:

            month_savings_rate = 0

        monthly_savings.append(
            {
                "year": month["year"],
                "month": month["month"],
                "income": month["income"],
                "expense": month["expense"],
                "savings": month_savings,
                "savings_rate": round(
                    month_savings_rate,
                    2
                )
            }
        )

    # ==========================================
    # RETURN AI CONTEXT
    # ==========================================

    return {

        "overall": {

            "total_income": total_income,

            "total_expense": total_expense,

            "savings": savings,

            "savings_rate": round(
                savings_rate,
                2
            )
        },

        "latest_month": latest_month,

        "previous_month": previous_month,

        "changes": {

            "expense_change_percent": (
                round(
                    expense_change,
                    2
                )
                if expense_change is not None
                else None
            ),

            "income_change_percent": (
                round(
                    income_change,
                    2
                )
                if income_change is not None
                else None
            )
        },

        "latest_categories": latest_categories,

        "top_expense_category": top_category,

        "top_category_percentage": (
            round(
                top_category_percentage,
                2
            )
            if top_category_percentage is not None
            else None
        ),

        "monthly_history": monthly_report,

        "monthly_savings_history": monthly_savings
    }

def add_goal_savings(user_id,goal_id,amount):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT g.currency,u.currency FROM goals g JOIN users u ON u.id=g.user_id WHERE g.id=%s AND g.user_id=%s FOR UPDATE",(goal_id,user_id)); row=cur.fetchone()
            if not row: conn.rollback(); return None
            goal_currency=row[0] or row[1] or "INR"; user_currency=row[1] or "INR"
            converted=convert_amount(amount,user_currency,goal_currency,datetime.now().date()) if user_currency!=goal_currency else float(amount)
            cur.execute("UPDATE goals SET current_amount=LEAST(target_amount,current_amount+%s) WHERE id=%s AND user_id=%s RETURNING id,name,target_amount,current_amount,target_date",(converted,goal_id,user_id)); result=cur.fetchone()
        conn.commit(); return result
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def batch_add_transactions(user_id, transactions):
    """Insert many normalized transactions in one database transaction."""
    if not transactions:
        return 0
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT currency FROM users WHERE id=%s",(user_id,)); row=cur.fetchone(); user_currency=(row[0] if row else "INR") or "INR"
            values=[(user_id,t["transaction_type"],t["amount"],t.get("currency",user_currency),t["category"],t["description"],t["date"],t.get("source","import")) for t in transactions]
            cur.executemany("""INSERT INTO transactions (user_id,transaction_type,amount,currency,category,description,date,source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""", values)
        conn.commit()
        return len(values)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def find_existing_transaction_keys(user_id, candidates):
    """Return duplicate keys for (date,description,type,amount) in one query."""
    if not candidates:
        return set()
    conn=get_connection()
    found=set()
    try:
        with conn.cursor() as cur:
            for d,desc,typ,amount in candidates:
                cur.execute("""
                    SELECT 1 FROM transactions
                    WHERE user_id=%s AND date=%s AND lower(description)=lower(%s)
                      AND transaction_type=%s AND amount=%s LIMIT 1
                """,(user_id,d,desc,typ,amount))
                if cur.fetchone():
                    found.add((d,desc.lower(),typ,round(float(amount),2)))
    finally:
        conn.close()
    return found

# =====================================================
# FINANCIAL ACCOUNTS / BANK CONNECTIONS
# =====================================================

def list_financial_accounts(user_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,provider,provider_account_id,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at,created_at FROM financial_accounts WHERE user_id=%s ORDER BY id DESC""", (user_id,))
            rows=cur.fetchall()
        return [{"id":r[0],"provider":r[1],"provider_account_id":r[2],"institution_name":r[3],"account_name":r[4],"account_type":r[5],"country":r[6],"currency":r[7],"masked_account":r[8],"balance":float(r[9]) if r[9] is not None else None,"status":r[10],"last_synced_at":str(r[11]) if r[11] else None,"created_at":str(r[12])} for r in rows]
    finally: conn.close()


def create_bank_connection(user_id, provider, consent_id, status="pending"):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO bank_connections(user_id,provider,consent_id,status) VALUES(%s,%s,%s,%s) ON CONFLICT(consent_id) DO UPDATE SET status=EXCLUDED.status,updated_at=CURRENT_TIMESTAMP RETURNING id""", (user_id,provider,consent_id,status))
            cid=cur.fetchone()[0]
        conn.commit(); return cid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def get_bank_connection(user_id, consent_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,user_id,provider,consent_id,data_session_id,status,consent_expires_at,last_sync_at FROM bank_connections WHERE user_id=%s AND consent_id=%s",(user_id,consent_id)); r=cur.fetchone()
        if not r: return None
        return {"id":r[0],"user_id":r[1],"provider":r[2],"consent_id":r[3],"data_session_id":r[4],"status":r[5],"consent_expires_at":str(r[6]) if r[6] else None,"last_sync_at":str(r[7]) if r[7] else None}
    finally: conn.close()


def update_bank_connection(user_id, consent_id, status=None, data_session_id=None, last_sync=False):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE bank_connections SET status=COALESCE(%s,status),data_session_id=COALESCE(%s,data_session_id),last_sync_at=CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE last_sync_at END,updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND consent_id=%s""",(status,data_session_id,last_sync,user_id,consent_id))
        conn.commit()
    finally: conn.close()


def import_external_transaction(user_id, tx, financial_account_id=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT transaction_id FROM external_transactions WHERE user_id=%s AND provider=%s AND external_id=%s",(user_id,tx["source"],tx["external_id"])); existing=cur.fetchone()
            if existing: return {"created":False,"transaction_id":existing[0]}
            # Keep automatic imports conservative: simple, deterministic categories.
            desc=tx["description"].lower()
            if tx.get("category"):
                category=tx["category"]
            elif tx["transaction_type"]=="income": category="Income"
            elif any(x in desc for x in ("swiggy","zomato","restaurant","food","cafe","domino")): category="Food"
            elif any(x in desc for x in ("uber","ola","metro","rapido","transport")): category="Transport"
            elif any(x in desc for x in ("amazon","flipkart","myntra","shopping")): category="Shopping"
            elif any(x in desc for x in ("rent","housing")): category="Housing"
            elif any(x in desc for x in ("electricity","water","gas","recharge","jio","airtel")): category="Bills"
            else: category="Other"
            cur.execute("""INSERT INTO transactions(user_id,transaction_type,amount,currency,category,description,date,source) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(user_id,tx["transaction_type"],tx["amount"],tx.get("currency","INR"),category,tx["description"],tx["date"],tx.get("source","setu_aa")))
            tid=cur.fetchone()[0]
            cur.execute("INSERT INTO external_transactions(user_id,financial_account_id,provider,external_id,transaction_id) VALUES(%s,%s,%s,%s,%s)",(user_id,financial_account_id,tx["source"],tx["external_id"],tid))
        conn.commit(); return {"created":True,"transaction_id":tid}
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def upsert_financial_account(user_id, provider, institution_name, account, country="India", currency="INR"):
    conn=get_connection()
    try:
        provider_account_id = account.get("linkedAccRef") or account.get("linkRefNumber")
        masked = account.get("maskedAccNumber")
        summary = account.get("summary") or {}
        balance_raw = summary.get("currentBalance") if isinstance(summary, dict) else None
        try:
            balance = float(balance_raw) if balance_raw not in (None, "") else None
        except (TypeError, ValueError):
            balance = None
        account_type = summary.get("type") if isinstance(summary, dict) else None
        account_type = account_type or account.get("type") or "deposit"
        account_name = account.get("name") or masked or institution_name
        with conn.cursor() as cur:
            existing = None
            if provider_account_id:
                cur.execute("SELECT id FROM financial_accounts WHERE user_id=%s AND provider=%s AND provider_account_id=%s ORDER BY id LIMIT 1", (user_id, provider, provider_account_id))
                existing = cur.fetchone()
            if existing:
                aid = existing[0]
                cur.execute("""UPDATE financial_accounts SET institution_name=%s,account_name=%s,account_type=%s,country=%s,currency=%s,masked_account=%s,balance=%s,status='connected',last_synced_at=CURRENT_TIMESTAMP WHERE id=%s AND user_id=%s""", (institution_name, account_name, account_type, country, currency, masked, balance, aid, user_id))
            else:
                cur.execute("""INSERT INTO financial_accounts(user_id,provider,provider_account_id,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'connected',CURRENT_TIMESTAMP) RETURNING id""", (user_id, provider, provider_account_id, institution_name, account_name, account_type, country, currency, masked, balance))
                aid = cur.fetchone()[0]
        conn.commit(); return aid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def list_bank_connections(user_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT consent_id,status,last_sync_at FROM bank_connections WHERE user_id=%s ORDER BY id DESC",(user_id,)); rows=cur.fetchall()
        return [{"consent_id":r[0],"status":r[1],"last_sync_at":str(r[2]) if r[2] else None} for r in rows]
    finally: conn.close()

def get_bank_connection_by_consent(consent_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id,status FROM bank_connections WHERE consent_id=%s",(consent_id,)); r=cur.fetchone()
        return {"user_id":r[0],"status":r[1]} if r else None
    finally: conn.close()
