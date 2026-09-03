import os
import uuid

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
        cur.execute("SELECT t.id,t.transaction_type,t.amount,t.currency,t.category,t.description,t.date,t.source,t.created_at,t.financial_account_id,f.account_name,f.institution_name FROM transactions t LEFT JOIN financial_accounts f ON f.id=t.financial_account_id WHERE t.user_id=%s ORDER BY t.date DESC,t.id DESC",(user_id,)); rows=cur.fetchall()
    conn.close()
    return [{"id":r[0],"transaction_type":r[1],"amount":float(r[2]),"currency":r[3] or "INR","category":r[4],"description":r[5],"date":str(r[6]),"source":r[7],"created_at":str(r[8]),"financial_account_id":r[9],"account_name":r[10],"institution_name":r[11]} for r in rows]


def delete_transaction(user_id, transaction_id):

    conn = get_connection()

    with conn.cursor() as cur:

        cur.execute("SELECT transfer_group_id FROM transactions WHERE id=%s AND user_id=%s", (transaction_id,user_id))
        row=cur.fetchone()
        if row and row[0]:
            cur.execute("DELETE FROM transactions WHERE user_id=%s AND transfer_group_id=%s", (user_id,row[0]))
        else:
            cur.execute("DELETE FROM transactions WHERE id=%s AND user_id=%s", (transaction_id,user_id))

    conn.commit()
    conn.close()


def get_transaction(user_id,transaction_id):
    conn=get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id,transaction_type,amount,currency,category,description,date,source,created_at,financial_account_id FROM transactions WHERE id=%s AND user_id=%s",(transaction_id,user_id)); r=cur.fetchone()
    conn.close()
    if r is None: return None
    return {"id":r[0],"transaction_type":r[1],"amount":float(r[2]),"currency":r[3] or "INR","category":r[4],"description":r[5],"date":str(r[6]),"source":r[7],"created_at":str(r[8]),"financial_account_id":r[9]}


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


def add_transaction(user_id, transaction_type, amount, category, description, date, source="manual", currency=None, financial_account_id=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if not currency:
                cur.execute("SELECT currency FROM users WHERE id=%s", (user_id,)); row=cur.fetchone(); currency=(row[0] if row else "INR") or "INR"
            cur.execute("""INSERT INTO transactions (user_id,transaction_type,amount,currency,category,description,date,source,financial_account_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""", (user_id,transaction_type,amount,currency,category,description,date,source,financial_account_id))
            tid=cur.fetchone()[0]
        conn.commit(); return tid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()



def create_transfer(user_id, amount, from_account_id, to_account_id, description, date, currency=None):
    """Move money between two owned accounts without creating income/expense."""
    if int(from_account_id) == int(to_account_id):
        raise ValueError("Choose two different accounts.")
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id,currency FROM financial_accounts WHERE user_id=%s AND id IN (%s,%s)", (user_id,from_account_id,to_account_id))
            rows=cur.fetchall()
            if len(rows) != 2:
                raise ValueError("Choose valid accounts you own.")
            currencies={r[0]:(r[1] or currency or 'INR') for r in rows}
            if currencies[int(from_account_id)] != currencies[int(to_account_id)]:
                raise ValueError("Transfers between different account currencies need an explicit FX amount and are not supported yet.")
            curcode=currency or currencies[int(from_account_id)]
            group=uuid.uuid4().hex
            cur.execute("""INSERT INTO transactions(user_id,transaction_type,amount,currency,category,description,date,source,financial_account_id,transfer_group_id)
                           VALUES(%s,'transfer_out',%s,%s,'Transfer',%s,%s,'manual_transfer',%s,%s)""",
                        (user_id,amount,curcode,description,date,from_account_id,group))
            cur.execute("""INSERT INTO transactions(user_id,transaction_type,amount,currency,category,description,date,source,financial_account_id,transfer_group_id)
                           VALUES(%s,'transfer_in',%s,%s,'Transfer',%s,%s,'manual_transfer',%s,%s)""",
                        (user_id,amount,curcode,description,date,to_account_id,group))
        conn.commit(); return group
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


def get_or_create_physical_cash_account(user_id, currency='INR', opening_balance=None):
    """Return the user's single Physical Cash account, creating it on first use."""
    ensure_financial_account_balance_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM financial_accounts WHERE user_id=%s AND account_type='cash' ORDER BY id LIMIT 1", (user_id,))
            row=cur.fetchone()
            if row:
                return row[0]
            if opening_balance is None:
                raise ValueError("Enter your current physical cash balance the first time you use Physical Cash.")
            cur.execute("""INSERT INTO financial_accounts
                (user_id,provider,institution_name,account_name,account_type,country,currency,balance,status,last_synced_at,balance_as_of)
                VALUES(%s,'manual','Cash','Physical Cash','cash','India',%s,%s,'manual',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING id""",
                (user_id,currency,opening_balance))
            aid=cur.fetchone()[0]
        conn.commit(); return aid
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()


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

_financial_balance_schema_ready = False

def ensure_financial_account_balance_schema():
    """Add a balance checkpoint without destructive migrations.

    balance is the user/provider supplied balance at balance_as_of. Manual
    transactions created after that checkpoint are applied when displaying a
    live balance, preventing statement imports from being counted twice.
    """
    global _financial_balance_schema_ready
    if _financial_balance_schema_ready:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE financial_accounts ADD COLUMN IF NOT EXISTS balance_as_of TIMESTAMP")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transfer_group_id VARCHAR(64)")
        conn.commit()
        _financial_balance_schema_ready = True
    finally:
        conn.close()

def _account_live_balance(base_balance, account_type, balance_as_of, income_after, expense_after):
    if base_balance is None:
        return None
    base = float(base_balance)
    typ = str(account_type or '').lower()
    income_after = float(income_after or 0)
    expense_after = float(expense_after or 0)
    if typ == 'credit_card':
        return max(0.0, base + expense_after - income_after)
    if typ in {'loan', 'liability', 'bnpl'}:
        # Remaining principal/outstanding is a checkpoint value. Generic expense
        # transactions can include interest, so do not guess principal reduction.
        return max(0.0, base)
    return base + income_after - expense_after


def list_financial_accounts(user_id):
    ensure_financial_account_balance_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,provider,provider_account_id,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at,created_at,balance_as_of FROM financial_accounts WHERE user_id=%s ORDER BY id DESC""", (user_id,))
            rows=cur.fetchall()
            out=[]
            for r in rows:
                cur.execute("""SELECT
                    COALESCE(SUM(CASE WHEN transaction_type IN ('income','transfer_in') AND (%s::timestamp IS NULL OR created_at > %s::timestamp) THEN amount ELSE 0 END),0),
                    COALESCE(SUM(CASE WHEN transaction_type IN ('expense','transfer_out') AND (%s::timestamp IS NULL OR created_at > %s::timestamp) THEN amount ELSE 0 END),0)
                    FROM transactions WHERE user_id=%s AND financial_account_id=%s""",
                    (r[13],r[13],r[13],r[13],user_id,r[0]))
                movement=cur.fetchone()
                live=_account_live_balance(r[9],r[5],r[13],movement[0],movement[1])
                out.append({"id":r[0],"provider":r[1],"provider_account_id":r[2],"institution_name":r[3],"account_name":r[4],"account_type":r[5],"country":r[6],"currency":r[7],"masked_account":r[8],"balance":float(r[9]) if r[9] is not None else None,"live_balance":live,"status":r[10],"last_synced_at":str(r[11]) if r[11] else None,"created_at":str(r[12]),"balance_as_of":str(r[13]) if r[13] else None})
        return out
    finally: conn.close()



def get_financial_account_activity(user_id, account_id, limit=100):
    """All transactions assigned to an owned account, manual or imported."""
    ensure_financial_account_balance_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT balance,account_type,balance_as_of FROM financial_accounts WHERE user_id=%s AND id=%s",(user_id,account_id))
            ar=cur.fetchone()
            if not ar:
                return {"transactions":[],"income":0.0,"expenses":0.0,"count":0,"first_date":None,"last_date":None,"categories":[],"live_balance":None}
            cur.execute("""SELECT id,transaction_type,amount,currency,category,description,date,source,created_at FROM transactions
                           WHERE user_id=%s AND financial_account_id=%s ORDER BY date DESC,id DESC LIMIT %s""",(user_id,account_id,limit)); rows=cur.fetchall()
            cur.execute("""SELECT COALESCE(SUM(CASE WHEN transaction_type='income' THEN amount ELSE 0 END),0),
                         COALESCE(SUM(CASE WHEN transaction_type='expense' THEN amount ELSE 0 END),0),COUNT(*),MIN(date),MAX(date),
                         COALESCE(SUM(CASE WHEN transaction_type IN ('income','transfer_in') AND (%s::timestamp IS NULL OR created_at > %s::timestamp) THEN amount ELSE 0 END),0),
                         COALESCE(SUM(CASE WHEN transaction_type IN ('expense','transfer_out') AND (%s::timestamp IS NULL OR created_at > %s::timestamp) THEN amount ELSE 0 END),0)
                         FROM transactions WHERE user_id=%s AND financial_account_id=%s""",(ar[2],ar[2],ar[2],ar[2],user_id,account_id)); sm=cur.fetchone()
            cur.execute("""SELECT category,COALESCE(SUM(amount),0) FROM transactions WHERE user_id=%s AND financial_account_id=%s AND transaction_type='expense' GROUP BY category ORDER BY SUM(amount) DESC LIMIT 5""",(user_id,account_id)); cats=cur.fetchall()
        tx=[{"id":r[0],"transaction_type":r[1],"amount":float(r[2]),"currency":r[3] or "INR","category":r[4],"description":r[5],"date":str(r[6]),"source":r[7],"created_at":str(r[8])} for r in rows]
        live=_account_live_balance(ar[0],ar[1],ar[2],sm[5],sm[6])
        return {"transactions":tx,"income":float(sm[0]),"expenses":float(sm[1]),"count":int(sm[2]),"first_date":str(sm[3]) if sm[3] else None,"last_date":str(sm[4]) if sm[4] else None,"categories":[{"category":r[0],"amount":float(r[1])} for r in cats],"live_balance":live}
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
            cur.execute("""INSERT INTO transactions(user_id,transaction_type,amount,currency,category,description,date,source,financial_account_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",(user_id,tx["transaction_type"],tx["amount"],tx.get("currency","INR"),category,tx["description"],tx["date"],tx.get("source","setu_aa"),financial_account_id))
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
                cur.execute("""UPDATE financial_accounts SET institution_name=%s,account_name=%s,account_type=%s,country=%s,currency=%s,masked_account=%s,balance=%s,status='connected',last_synced_at=CURRENT_TIMESTAMP,balance_as_of=CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE balance_as_of END WHERE id=%s AND user_id=%s""", (institution_name, account_name, account_type, country, currency, masked, balance, balance, aid, user_id))
            else:
                cur.execute("""INSERT INTO financial_accounts(user_id,provider,provider_account_id,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at,balance_as_of) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'connected',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING id""", (user_id, provider, provider_account_id, institution_name, account_name, account_type, country, currency, masked, balance))
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


def create_manual_financial_account(user_id, institution_name, account_name, account_type='savings', currency='INR', masked_account=None, balance=None, country='India'):
    """Create a user-managed financial account for statement imports. Never stores credentials."""
    ensure_financial_account_balance_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""INSERT INTO financial_accounts
                (user_id,provider,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at,balance_as_of)
                VALUES(%s,'statement',%s,%s,%s,%s,%s,%s,%s,'statement',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) RETURNING id""",
                (user_id,institution_name,account_name or institution_name,account_type,country,currency,masked_account,balance))
            aid=cur.fetchone()[0]
        conn.commit(); return aid
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


def get_financial_account(user_id, account_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT id,provider,institution_name,account_name,account_type,country,currency,masked_account,balance,status,last_synced_at,balance_as_of
                           FROM financial_accounts WHERE user_id=%s AND id=%s""",(user_id,account_id)); r=cur.fetchone()
        if not r: return None
        return {"id":r[0],"provider":r[1],"institution_name":r[2],"account_name":r[3],"account_type":r[4],"country":r[5],"currency":r[6],"masked_account":r[7],"balance":float(r[8]) if r[8] is not None else None,"status":r[9],"last_synced_at":str(r[10]) if r[10] else None,"balance_as_of":str(r[11]) if len(r)>11 and r[11] else None}
    finally: conn.close()


def touch_financial_account(user_id, account_id, balance=None):
    ensure_financial_account_balance_schema()
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE financial_accounts SET last_synced_at=CURRENT_TIMESTAMP,
                           balance=COALESCE(%s,balance),
                           balance_as_of=CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE balance_as_of END
                           WHERE user_id=%s AND id=%s""",(balance,balance,user_id,account_id))
        conn.commit()
    finally: conn.close()

def find_duplicate_manual_financial_account(user_id, institution_name, account_name, account_type, masked_account=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if masked_account:
                cur.execute("""SELECT id FROM financial_accounts WHERE user_id=%s AND provider='statement' AND lower(trim(institution_name))=lower(trim(%s)) AND account_type=%s AND masked_account=%s LIMIT 1""",(user_id,institution_name,account_type,masked_account))
            else:
                cur.execute("""SELECT id FROM financial_accounts WHERE user_id=%s AND provider='statement' AND lower(trim(institution_name))=lower(trim(%s)) AND lower(trim(account_name))=lower(trim(%s)) AND account_type=%s AND COALESCE(masked_account,'')='' LIMIT 1""",(user_id,institution_name,account_name,account_type))
            r=cur.fetchone(); return r[0] if r else None
    finally: conn.close()

def update_financial_account(user_id, account_id, institution_name, account_name, account_type, currency, masked_account=None, balance=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""UPDATE financial_accounts SET institution_name=%s,account_name=%s,account_type=%s,currency=%s,masked_account=%s,balance=%s,
                           balance_as_of=CASE WHEN %s IS NOT NULL THEN CURRENT_TIMESTAMP ELSE balance_as_of END
                           WHERE user_id=%s AND id=%s""",(institution_name,account_name,account_type,currency,masked_account,balance,balance,user_id,account_id))
        conn.commit()
    finally: conn.close()

def delete_financial_account(user_id, account_id):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE transactions SET financial_account_id=NULL WHERE user_id=%s AND financial_account_id=%s",(user_id,account_id))
            cur.execute("DELETE FROM financial_accounts WHERE user_id=%s AND id=%s",(user_id,account_id))
        conn.commit()
    finally: conn.close()

def assign_transaction_account(user_id, transaction_id, account_id=None):
    conn=get_connection()
    try:
        with conn.cursor() as cur:
            if account_id:
                cur.execute("SELECT 1 FROM financial_accounts WHERE id=%s AND user_id=%s",(account_id,user_id))
                if not cur.fetchone(): raise ValueError('Invalid account')
            cur.execute("UPDATE transactions SET financial_account_id=%s WHERE id=%s AND user_id=%s",(account_id,transaction_id,user_id))
        conn.commit()
    finally: conn.close()
