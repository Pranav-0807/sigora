from ai_insights import(get_ai_insights,
                        get_goal_ai_insight,
                        get_budget_ai_insight,
                        get_dashboard_ai_insight,
                        get_investment_ai_insight,
                    ) 
import os
from flask import Flask, render_template, redirect, request, session, flash, send_file, jsonify
import csv
import hmac
import hashlib
import requests
from datetime import datetime
from import_engine import read_statement, normalize_rows
from currency_engine import convert_transaction, convert_amount
from financial_intelligence import build_intelligence, simulate_purchase
from io import BytesIO, StringIO
from werkzeug.security import generate_password_hash
from database import (
    get_transactions,
    delete_transaction,
    get_transaction,
    update_transaction,
    add_transaction as db_add_transaction,
    create_user,
    get_user_by_email,
    get_user_by_id,
    check_user_password,
    get_goals,
    add_goal,
    delete_goal,
    get_budgets,
    add_budget,
    delete_budget,
    update_goal,
    get_monthly_savings,
    update_budget,
    get_budget_spending,
    get_report_totals,
    get_monthly_report,
    get_expense_categories,
    get_expense_categories_by_period,
    get_connection,
    get_ai_financial_context,
    add_goal_savings,
    batch_add_transactions,
    find_existing_transaction_keys,
    list_financial_accounts,
    list_bank_connections,
    create_bank_connection,
    get_bank_connection,
    get_bank_connection_by_consent,
    update_bank_connection,
    import_external_transaction,
    upsert_financial_account,
)

from investment_features import (
    ensure_investment_schema, get_profile, save_profile, model_allocation,
    add_investment, update_investment_price, delete_investment, portfolio_summary,
    add_watchlist, delete_watchlist, get_watchlist, financial_investment_context, EXPLORER
)

from bank_integration import configured as setu_configured, create_consent, get_consent, create_session, get_session, parse_transactions, parse_accounts

from product_features import (
    ensure_feature_schema,
    get_user_settings,
    update_user_settings,
    change_user_password,
    delete_user_account,
    get_gamification,
    award_activity,
    get_alerts,
    mark_alert_read,
    sync_financial_alerts,
    send_email_alert,
    send_transactional_email,
    create_password_reset_token,
    password_reset_token_is_valid,
    reset_password_with_token,
    premium_features,
    get_ai_usage,
    consume_ai_request,
    get_ai_limits,
    get_premium_status,
    mark_subscription_cancellation_requested,
    submit_support_message,
    COUNTRY_CURRENCIES,
    COUNTRIES,
    currency_for_country,
    get_pricing,
    ensure_monetization_schema,
    list_coupons,
    create_coupon,
    toggle_coupon,
    remember_subscription_coupon,
    redeem_subscription_coupon,
    get_user_id_for_subscription,
    get_razorpay_subscription_id,
)
app = Flask(__name__)

# Keep secrets out of source code. Set SECRET_KEY in the deployment environment.
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

@app.before_request
def _ensure_launch_schema():
    ensure_feature_schema()
    ensure_investment_schema()

# Production defaults
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("IMPORT_MAX_FILE_MB", "25")) * 1024 * 1024

@app.context_processor
def inject_sigora_globals():
    user = get_current_user()
    currency = (user or {}).get("currency", "INR")
    country = (user or {}).get("country", "India")
    pricing = get_pricing(currency, country)
    symbols = {"INR":"₹","USD":"$","EUR":"€","GBP":"£","CAD":"C$","AUD":"A$","CHF":"CHF","SGD":"S$","AED":"د.إ","JPY":"¥","NZD":"NZ$","ZAR":"R"}
    return {
        "currency_symbol": symbols.get(currency, currency),
        "currency_code": currency,
        "premium_price": pricing["premium_price"],
        "premium_currency_symbol": pricing.get("currency_symbol", "₹"),
        "premium_currency_code": pricing.get("currency", "INR"),
        "support_email": os.getenv("SIGORA_SUPPORT_EMAIL", "").strip(),
        "sigora_countries": COUNTRIES,
        "country_currencies": COUNTRY_CURRENCIES,
        "currency_options": sorted({pair for pair in COUNTRY_CURRENCIES.values()}),
        "ga4_measurement_id": os.getenv("SIGORA_GA4_MEASUREMENT_ID", "").strip(),
    }

@app.template_filter("money")
def money_filter(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)

def load_transactions():
    transactions = []

    try:
        with open("../Sigora/transaction.csv", "r", newline="") as file:
            reader = csv.DictReader(file)

            for index,row in enumerate(reader, start=1):

                if "id" not in row or not row["id"]:
                    row["id"] = str(index)
                transactions.append(row)

    except FileNotFoundError:
        pass

    return transactions

def save_transactions(transactions):
    with open("../Sigora/transaction.csv", "w", newline="") as file:
        fieldnames = [
            "id",
            "transaction_type",
            "amount",
            "category",
            "description",
            "date"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()

        for transaction in transactions:
            writer.writerow({
                "id": transaction["id"],
                "transaction_type": transaction["transaction_type"],
                "amount": transaction["amount"],
                "category": transaction["category"],
                "description": transaction["description"],
                "date": transaction["date"]
            })

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():

    user = get_current_user()

    if not user:
        return redirect("/login")

    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]

    # ==========================================
    # BASIC FINANCIAL TOTALS
    # ==========================================

    total_income = 0
    total_expense = 0

    for transaction in transactions:

        amount = float(transaction["amount"])

        transaction_type = (
            transaction["transaction_type"]
            .strip()
            .lower()
        )

        if transaction_type == "income":
            total_income += amount

        elif transaction_type == "expense":
            total_expense += amount


    balance = total_income - total_expense

    transaction_count = len(transactions)


    # ==========================================
    # SAVINGS
    # ==========================================

    if total_income > 0:

        savings_rate = (
            (balance / total_income) * 100
        )

    else:

        savings_rate = 0


    # ==========================================
    # LAST TRANSACTION
    # ==========================================

    if transactions:

        last_transaction = max(
            transactions,
            key=lambda transaction: datetime.strptime(
                transaction["date"],
                "%Y-%m-%d"
            )
        )

    else:

        last_transaction = None


    # ==========================================
    # EXPENSE CATEGORY TOTALS
    # ==========================================

    expense_category_totals = {}

    for transaction in transactions:

        if transaction["transaction_type"].strip().lower() != "expense":
            continue

        category = transaction.get("category")

        if not category:
            category = "Other"

        # Normalize category names
        # Food, food, FOOD -> Food
        category = category.strip().title()

        amount = float(transaction["amount"])

        if category in expense_category_totals:

            expense_category_totals[category] += amount

        else:

            expense_category_totals[category] = amount


    # ==========================================
    # TOP EXPENSE CATEGORY
    # ==========================================

    if expense_category_totals:

        top_expense_category = max(
            expense_category_totals,
            key=expense_category_totals.get
        )

        top_amount = (
            expense_category_totals[
                top_expense_category
            ]
        )

    else:

        top_expense_category = None
        top_amount = 0


    # ==========================================
    # SPENDING BREAKDOWN
    # ==========================================

    expense_breakdown = []

    for category, amount in expense_category_totals.items():

        if total_expense > 0:

            percentage = (
                amount / total_expense
            ) * 100

        else:

            percentage = 0


        expense_breakdown.append({

            "category": category,

            "amount": amount,

            "percentage": percentage

        })


    # Largest expenses first
    expense_breakdown.sort(
        key=lambda item: item["amount"],
        reverse=True
    )


    # ==========================================
    # DASHBOARD ALERT
    # ==========================================

    dashboard_alert = None
    dashboard_alert_type = "neutral"

    if not transactions:

        dashboard_alert = (
            "Start by adding your first transaction "
            "to unlock your financial insights."
        )

        dashboard_alert_type = "neutral"


    elif total_income == 0 and total_expense > 0:

        dashboard_alert = (
            "You currently have expenses recorded "
            "but no income recorded. Add your income "
            "to get a clearer picture of your balance."
        )

        dashboard_alert_type = "warning"


    elif balance < 0:

        dashboard_alert = (
            "Your expenses are currently higher than "
            "your recorded income. Review your spending "
            "before taking on additional expenses."
        )

        dashboard_alert_type = "danger"


    elif savings_rate >= 30:

        dashboard_alert = (
            "Strong position — you're currently keeping "
            "a healthy portion of your recorded income."
        )

        dashboard_alert_type = "positive"


    elif savings_rate >= 10:

        dashboard_alert = (
            "You're saving some of your recorded income. "
            "Keep an eye on your largest spending categories "
            "to create more room if needed."
        )

        dashboard_alert_type = "neutral"


    else:

        dashboard_alert = (
            "Your current savings margin is fairly small. "
            "Review your largest discretionary expenses "
            "if you want to create more breathing room."
        )

        dashboard_alert_type = "warning"


    # ==========================================
    # RECENT TRANSACTIONS
    # ==========================================

    recent_transactions = transactions[:5]


    # ==========================================
    # LAUNCH FEATURES
    # ==========================================

    gamification = get_gamification(user["id"])
    current_month = datetime.now().month
    current_year = datetime.now().year
    dashboard_budgets = get_budgets(user["id"], current_month, current_year)
    for budget in dashboard_budgets:
        budget["spent"] = get_budget_spending(user["id"], budget["category"], current_month, current_year)
    dashboard_goals = get_goals(user["id"])

    # Alerts are useful, but must never take the core dashboard down.
    # If a provider/database alert migration fails, Sigora still renders.
    try:
        sync_financial_alerts(user["id"], dashboard_budgets, dashboard_goals)
    except Exception as exc:
        app.logger.exception("Financial alert sync failed: %s", exc)

    try:
        alerts = get_alerts(user["id"], 6)
    except Exception as exc:
        app.logger.exception("Financial alert load failed: %s", exc)
        alerts = []

    # ==========================================
    # RENDER
    # ==========================================

    return render_template(

        "dashboard.html",

        user=user,

        transactions=transactions,

        recent_transactions=recent_transactions,

        total_income=total_income,

        total_expense=total_expense,

        balance=balance,

        transaction_count=transaction_count,

        last_transaction=last_transaction,

        expense_category_totals=expense_category_totals,

        expense_breakdown=expense_breakdown,

        top_expense_category=top_expense_category,

        top_amount=top_amount,

        savings_rate=savings_rate,

        dashboard_alert=dashboard_alert,

        dashboard_alert_type=dashboard_alert_type,
        gamification=gamification,
        alerts=alerts

    )

def run_limited_ai(user_id, generator, *args):
    status = get_premium_status(user_id)
    usage = consume_ai_request(user_id, status["is_premium"])
    if not usage["allowed"]:
        if usage["reason"] == "daily":
            return f"AI daily limit reached ({usage['daily_limit']}/day). Please try again tomorrow."
        if usage["reason"] == "budget":
            return "Sigora AI monthly safety budget has been reached. AI is paused until the next billing month."
        if usage["reason"] == "global":
            return "Sigora AI has reached its platform safety limit for this month. Please try again later."
        return f"AI monthly limit reached ({usage['limit']}/month). Upgrade to Premium for a larger monthly allowance."
    return generator(*args)


@app.route("/transactions")
def transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")

    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]
    search = request.args.get("search", "").strip().lower()
    transaction_type = request.args.get("transaction_type", "all").lower()
    category = request.args.get("category", "all").strip().lower()

    if search:
        transactions = [t for t in transactions if search in str(t.get("transaction_type", "")).lower() or search in str(t.get("description", "")).lower() or search in str(t.get("category", "")).lower()]
    if transaction_type != "all":
        transactions = [t for t in transactions if str(t.get("transaction_type", "")).lower() == transaction_type]
    if category != "all":
        transactions = [t for t in transactions if str(t.get("category", "")).lower() == category]

    categories = sorted({str(t.get("category", "Other")).strip().title() for t in get_transactions(user["id"]) if t.get("category")})
    total_income = sum(float(t["amount"]) for t in transactions if str(t["transaction_type"]).lower() == "income")
    total_expense = sum(float(t["amount"]) for t in transactions if str(t["transaction_type"]).lower() == "expense")
    return render_template("transactions.html", transactions=transactions, search=search, transaction_type=transaction_type, category=category, categories=categories, total_income=total_income, total_expense=total_expense, balance=total_income-total_expense)

@app.route("/transactions/export")
def export_transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")
    transactions = [convert_transaction(t, user.get("currency", "INR")) for t in get_transactions(user["id"])]
    search = request.args.get("search", "").strip().lower()
    transaction_type = request.args.get("transaction_type", "all").lower()
    category = request.args.get("category", "all").strip().lower()
    if search:
        transactions = [t for t in transactions if search in str(t.get("transaction_type", "")).lower() or search in str(t.get("description", "")).lower() or search in str(t.get("category", "")).lower()]
    if transaction_type != "all":
        transactions = [t for t in transactions if str(t.get("transaction_type", "")).lower() == transaction_type]
    if category != "all":
        transactions = [t for t in transactions if str(t.get("category", "")).lower() == category]

    fmt = request.args.get("format", "csv").lower()
    rows = [["Date", "Type", "Category", "Description", "Amount"]]
    rows += [[t.get("date", ""), str(t.get("transaction_type", "")).title(), t.get("category", ""), t.get("description", ""), float(t.get("amount", 0))] for t in transactions]
    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Transactions"
        for row in rows: ws.append(row)
        ws.freeze_panes = "A2"
        ws.column_dimensions["A"].width = 14; ws.column_dimensions["B"].width = 12; ws.column_dimensions["C"].width = 20; ws.column_dimensions["D"].width = 40; ws.column_dimensions["E"].width = 16
        out = BytesIO(); wb.save(out); out.seek(0)
        return send_file(out, as_attachment=True, download_name="sigora_transactions.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    out = StringIO(); writer = csv.writer(out); writer.writerows(rows); out.seek(0)
    return send_file(BytesIO(out.getvalue().encode("utf-8-sig")), as_attachment=True, download_name="sigora_transactions.csv", mimetype="text/csv")

@app.route("/delete/<transaction_id>")
def delete_transaction_route(transaction_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_transaction(user["id"], transaction_id)

    return redirect("/transactions")

@app.route("/edit/<transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    transaction = get_transaction(user["id"], transaction_id)

    if not transaction:
        return "Transaction not found", 404
    

    if request.method == "POST":
       try:
              amount = float(request.form["amount"])

              if amount <= 0:
                   return render_template(
                       "edit_transaction.html",
                       transaction=transaction,
                       error="Amount must be greater than 0."
                   )
       except ValueError:
              return render_template(
                  "edit_transaction.html",
                  transaction=transaction,
                  error="Invalid amount. Please enter a valid number."
              )

       category = request.form["category"].strip()

       if not category:
              return render_template(
                 "edit_transaction.html",
                 transaction=transaction,
                 error="Category cannot be empty."
         )

       description = request.form["description"].strip()

       if not description:
              return render_template(
                "edit_transaction.html",
                transaction=transaction,
                error="Description cannot be empty."
         )

       date = request.form["date"]

       try:
             datetime.strptime(date, "%Y-%m-%d")
       except ValueError:
             return render_template(
              "edit_transaction.html",
              transaction=transaction,
              error="Please enter a valid date."
       )

       update_transaction(
            user["id"],
            transaction_id,
            request.form["transaction_type"],
            amount,
            category,
            description,
            date
    )

       return redirect("/transactions")
    
    return render_template(
        "edit_transaction.html",
        transaction=transaction
    )

@app.route("/add-transaction", methods=["GET", "POST"])
def add_transaction():

     user = get_current_user()

     if not user:
         return redirect("/login")

     if request.method == "POST":
          transaction_type = request.form["transaction_type"]

          try:
              amount = float(request.form["amount"])
              if amount <=0:
                    return render_template(
                        "add_transaction.html",
                        error="Amount must be greater than 0."
                    )
          except ValueError:
                return render_template(
                    "add_transaction.html",
                    error="Invalid amount. Please enter a valid number."
                )
          category = request.form.get("category", "").strip()
          description = request.form["description"].strip()
          if not description:
                return render_template(
                    "add_transaction.html",
                    error="Description cannot be empty."
                )
          date = request.form["date"]
          try:
               datetime.strptime(date, "%Y-%m-%d")
          except ValueError:
                return render_template(
                    "add_transaction.html",
                    error="Please enter a valid date."
                )
          if not category or category.lower() in {"auto", "auto-categorize", "automatic"}:
              category = categorize_transaction(description, transaction_type)

          db_add_transaction(
            user["id"],
            transaction_type,
            amount,
            category,
            description,
            date
        )
          award_activity(user["id"], "transaction", 10)
          return redirect("/transactions?celebration=transaction")
     return render_template("add_transaction.html")         

@app.route("/budgets")
def budgets():

    user = get_current_user()

    if not user:
        return redirect("/login")


    # =================================================
    # CURRENT MONTH
    # =================================================

    now = datetime.now()

    month = now.month
    year = now.year


    # =================================================
    # GET BUDGETS
    # =================================================

    budgets = get_budgets(
        user["id"],
        month,
        year
    )


    # =================================================
    # GET EXPENSE CATEGORIES
    # =================================================

    expense_categories = get_expense_categories(
        user["id"]
    )


    # =================================================
    # PROCESS BUDGETS
    # =================================================

    for budget in budgets:

        # ---------------------------------------------
        # CURRENT SPENDING
        # ---------------------------------------------

        spent = get_budget_spending(
            user["id"],
            budget["category"],
            month,
            year
        )


        # ---------------------------------------------
        # REMAINING
        # ---------------------------------------------

        remaining = (
            budget["amount"] - spent
        )


        # ---------------------------------------------
        # PERCENTAGE USED
        # ---------------------------------------------

        percentage_used = (
            (spent / budget["amount"]) * 100
            if budget["amount"] > 0
            else 0
        )


        # ---------------------------------------------
        # STORE CALCULATED VALUES
        # ---------------------------------------------

        budget["spent"] = spent

        budget["remaining"] = remaining

        budget["percentage_used"] = (
            percentage_used
        )


        # ---------------------------------------------
        # STATUS
        # ---------------------------------------------

        if percentage_used >= 100:

            budget["status"] = "Over"

        elif percentage_used >= 75:

            budget["status"] = "Warning"

        else:

            budget["status"] = "Good"


        # ---------------------------------------------
        # BUDGET AI
        # ---------------------------------------------

        requested_ai_budget = request.args.get("ai_budget", type=int)
        budget["ai_insight"] = None
        if requested_ai_budget == budget.get("id"):
            budget["ai_insight"] = run_limited_ai(user["id"], get_budget_ai_insight, budget, expense_categories)


    # =================================================
    # RENDER
    # =================================================

    return render_template(
        "budgets.html",
        budgets=budgets,
        month=month,
        year=year
    )

@app.route("/add-budget", methods=["GET", "POST"])
def add_budget_route():

    user = get_current_user()

    if not user:
        return redirect("/login")

    if request.method == "POST":

        category = request.form["category"].strip()

        if not category:
            return render_template(
                "add_budget.html",
                error="Category cannot be empty."
            )

        try:
            amount = float(request.form["amount"])

            if amount <= 0:
                return render_template(
                    "add_budget.html",
                    error="Budget amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "add_budget.html",
                error="Please enter a valid budget amount."
            )

        month = int(request.form["month"])
        year = int(request.form["year"])

        if month < 1 or month > 12:
            return render_template(
                "add_budget.html",
                error="Please select a valid month."
            )

        if year < 2000:
            return render_template(
                "add_budget.html",
                error="Please enter a valid year."
            )

        budget_id=add_budget(
            user["id"],
            category,
            amount,
            month,
            year,
            user.get("currency", "INR")
        )

        if budget_id is None:

             return render_template(
                    "add_budget.html",
                    current_month=month,
                    current_year=year,
                    error=f"You already have a {category.title()} budget for this month."
                )


        award_activity(user["id"], "budget", 20)
        return redirect("/budgets?celebration=budget")

    now = datetime.now()

    return render_template(
        "add_budget.html",
        current_month=now.month,
        current_year=now.year
    )

@app.route("/delete-budget/<budget_id>")
def delete_budget_route(budget_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_budget(
        user["id"],
        budget_id
    )

    return redirect("/budgets")

@app.route("/edit-budget/<budget_id>", methods=["GET", "POST"])
def edit_budget(budget_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    now = datetime.now()

    budgets = get_budgets(
        user["id"],
        now.month,
        now.year
    )

    budget = None

    for item in budgets:
        if str(item["id"]) == str(budget_id):
            budget = item
            break

    if budget is None:
        return "Budget not found", 404

    if request.method == "POST":

        category = request.form["category"].strip()

        if not category:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Category cannot be empty."
            )

        try:
            amount = float(request.form["amount"])

            if amount <= 0:
                return render_template(
                    "edit_budget.html",
                    budget=budget,
                    error="Budget amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid budget amount."
            )

        try:
            month = int(request.form["month"])
            year = int(request.form["year"])

        except ValueError:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid month and year."
            )

        if month < 1 or month > 12:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please select a valid month."
            )

        if year < 2000:
            return render_template(
                "edit_budget.html",
                budget=budget,
                error="Please enter a valid year."
            )

        update_budget(
            user["id"],
            budget_id,
            category,
            amount,
            month,
            year,
            user.get("currency", "INR")
        )
        award_activity(user["id"], "budget", 10)
        return redirect("/budgets?celebration=budget")

    return render_template(
        "edit_budget.html",
        budget=budget
    )

@app.route("/goals")
def goals():

    user = get_current_user()

    if not user:
        return redirect("/login")

    # =================================================
    # GET GOALS
    # =================================================

    goals = get_goals(user["id"])

    # =================================================
    # GET MONTHLY SAVINGS
    # =================================================

    monthly_savings = get_monthly_savings(user["id"])

    positive_savings = [
        month["savings"]
        for month in monthly_savings
        if month["savings"] > 0
    ]

    if positive_savings:

        average_monthly_saving = (
            sum(positive_savings)
            / len(positive_savings)
        )

    else:

        average_monthly_saving = 0

    # =================================================
    # GET EXPENSE CATEGORIES
    # =================================================

    expense_categories = get_expense_categories(
        user["id"]
    )

    # =================================================
    # CURRENT DATE
    # =================================================

    today = datetime.now().date()

    # =================================================
    # PROCESS EACH GOAL
    # =================================================

    for goal in goals:

        target_amount = float(
            goal["target_amount"]
        )

        current_amount = float(
            goal["current_amount"]
        )

        # ---------------------------------------------
        # REMAINING AMOUNT
        # ---------------------------------------------

        remaining = max(
            target_amount - current_amount,
            0
        )

        # ---------------------------------------------
        # TARGET DATE
        # ---------------------------------------------

        target_date = datetime.strptime(
            str(goal["target_date"]),
            "%Y-%m-%d"
        ).date()

        days_remaining = (
            target_date - today
        ).days

        # ---------------------------------------------
        # GOAL STATUS
        # ---------------------------------------------

        if remaining <= 0:

            required_monthly_saving = 0

            likelihood = "Completed"

        elif days_remaining <= 0:

            required_monthly_saving = remaining

            likelihood = "Missed"

        else:

            months_remaining = max(
                days_remaining / 30.44,
                1
            )

            required_monthly_saving = (
                remaining / months_remaining
            )

            if average_monthly_saving <= 0:

                likelihood = "Low"

            elif (
                average_monthly_saving
                >= required_monthly_saving
            ):

                likelihood = "High"

            elif (
                average_monthly_saving
                >= required_monthly_saving * 0.7
            ):

                likelihood = "Medium"

            else:

                likelihood = "Low"

        # ---------------------------------------------
        # ADD CALCULATED VALUES
        # ---------------------------------------------

        goal["remaining"] = remaining

        goal["required_monthly_saving"] = (
            required_monthly_saving
        )

        goal["average_monthly_saving"] = (
            average_monthly_saving
        )

        goal["likelihood"] = likelihood

        # ---------------------------------------------
        # GOAL AI
        # ---------------------------------------------

        requested_ai_goal = request.args.get("ai_goal", type=int)
        goal["ai_insight"] = None
        if requested_ai_goal == goal.get("id"):
            goal["ai_insight"] = run_limited_ai(user["id"], get_goal_ai_insight, goal, expense_categories)

    # =================================================
    # RENDER PAGE
    # =================================================

    return render_template(
        "goals.html",
        goals=goals
    )


@app.route("/add-goal", methods=["GET", "POST"])
def add_goal_route():

    user = get_current_user()

    if not user:
        return redirect("/login")

    if request.method == "POST":

        name = request.form["name"].strip()

        if not name:
            return render_template(
                "add_goal.html",
                error="Goal name cannot be empty."
            )

        try:
            target_amount = float(request.form["target_amount"])

            if target_amount <= 0:
                return render_template(
                    "add_goal.html",
                    error="Target amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid target amount."
            )

        try:
            current_amount = float(request.form["current_amount"])

            if current_amount < 0:
                return render_template(
                    "add_goal.html",
                    error="Current amount cannot be negative."
                )

            if current_amount > target_amount:
                return render_template(
                    "add_goal.html",
                    error="Current amount cannot be greater than the target."
                )

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid current amount."
            )

        target_date = request.form["target_date"]

        try:
            datetime.strptime(target_date, "%Y-%m-%d")

        except ValueError:
            return render_template(
                "add_goal.html",
                error="Please enter a valid target date."
            )

        goal_id=add_goal(
            user["id"],
            name,
            target_amount,
            current_amount,
            target_date,
            user.get("currency", "INR")
        )

        if goal_id is None:

         return render_template(
                "add_goal.html",
                error="You already have this goal.",
            )

        award_activity(user["id"], "goal", 25)
        return redirect("/goals?celebration=goal")

    return render_template("add_goal.html")

@app.route("/edit-goal/<goal_id>", methods=["GET", "POST"])
def edit_goal(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    goals = get_goals(user["id"])

    goal = None

    for item in goals:
        if str(item["id"]) == str(goal_id):
            goal = item
            break

    if goal is None:
        return "Goal not found", 404

    if request.method == "POST":

        name = request.form["name"].strip()

        if not name:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Goal name cannot be empty."
            )

        try:
            target_amount = float(request.form["target_amount"])

            if target_amount <= 0:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Target amount must be greater than 0."
                )

        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid target amount."
            )

        try:
            current_amount = float(request.form["current_amount"])

            if current_amount < 0:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Current amount cannot be negative."
                )

            if current_amount > target_amount:
                return render_template(
                    "edit_goal.html",
                    goal=goal,
                    error="Current amount cannot be greater than the target."
                )

        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid current amount."
            )

        target_date = request.form["target_date"]

        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            return render_template(
                "edit_goal.html",
                goal=goal,
                error="Please enter a valid target date."
            )

        was_completed = float(goal["current_amount"]) >= float(goal["target_amount"])
        update_goal(
            user["id"],
            goal_id,
            name,
            target_amount,
            current_amount,
            target_date,
            user.get("currency", "INR")
        )
        award_activity(user["id"], "goal", 10)
        celebration = "goal-complete" if (current_amount >= target_amount and not was_completed) else "goal"
        if current_amount >= target_amount and not was_completed:
            award_activity(user["id"], "goal_completed", 75)
        return redirect(f"/goals?celebration={celebration}")

    return render_template(
        "edit_goal.html",
        goal=goal
    )

@app.route("/goals/<goal_id>/add-savings", methods=["POST"])
def add_goal_savings_route(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    try:
        amount = float(request.form.get("amount", ""))
    except (ValueError, TypeError):
        return redirect("/goals?error=invalid-savings")

    if amount <= 0:
        return redirect("/goals?error=invalid-savings")

    result = add_goal_savings(
        user["id"],
        goal_id,
        amount
    )

    if result is None:
        return redirect("/goals?error=goal-not-found")

    award_activity(user["id"], "goal", 10)

    # If the added amount completes the goal, award the completion activity once.
    if float(result[3]) >= float(result[2]):
        award_activity(user["id"], "goal_completed", 75)
        return redirect("/goals?celebration=goal-complete")

    return redirect("/goals?celebration=goal")


@app.route("/delete-goal/<goal_id>")
def delete_goal_route(goal_id):

    user = get_current_user()

    if not user:
        return redirect("/login")

    delete_goal(
        user["id"],
        goal_id
    )

    return redirect("/goals")

@app.route("/reports")
def reports():

    user = get_current_user()

    if not user:
        return redirect("/login")

    report = get_report_totals(user["id"])
    monthly_report = get_monthly_report(user["id"])
    category_report = get_expense_categories_by_period(user["id"])

    balance = (
        report["total_income"]
        - report["total_expense"]
    )

    return render_template(
        "reports.html",
        report=report,
        balance=balance,
        monthly_report = monthly_report,
        category_report = category_report
    )

@app.route("/signup", methods=["GET", "POST"])
def signup():
    ensure_feature_schema()
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            return render_template(
                "signup.html",
                error="Please fill in all fields."
            )

        existing_user = get_user_by_email(email)

        if existing_user:
            return render_template(
                "signup.html",
                error="An account with this email already exists."
            )

        country = request.form.get("country", "India").strip()
        if country not in COUNTRY_CURRENCIES:
            country = "India"
        currency, _ = currency_for_country(country)
        user_id = create_user(name, email, password, currency=currency, country=country)
        session["user_id"] = user_id
        return redirect("/dashboard")

    return render_template("signup.html", countries=COUNTRIES)

@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_feature_schema()
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = get_user_by_email(email)

        if not user:
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        if not check_user_password(
            password,
            user["password_hash"]
        ):
            return render_template(
                "login.html",
                error="Invalid email or password."
            )

        session["user_id"] = user["id"]

        return redirect("/dashboard")

    return render_template("login.html", changed=request.args.get("changed"))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    ensure_feature_schema()
    message = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_user_by_email(email) if email else None
        if user:
            token = create_password_reset_token(user["id"], ttl_minutes=30)
            if token:
                base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/") or request.url_root.rstrip("/")
                reset_url = f"{base_url}/reset-password/{token}"
                support_email = os.getenv("SIGORA_SUPPORT_EMAIL", "support.sigora@gmail.com").strip()
                body = (
                    f"Hi {user['name']},\n\n"
                    "We received a request to reset your Sigora password.\n\n"
                    f"Reset your password: {reset_url}\n\n"
                    "This link expires in 30 minutes and can only be used once. "
                    "If you did not request this, you can ignore this email; your password will stay unchanged.\n\n"
                    f"Need help? Contact {support_email}.\n\n"
                    "— Sigora"
                )
                send_transactional_email(user["email"], "Reset your Sigora password", body)
        message = "If an account exists for that email, a password reset link has been sent. Please check your inbox and spam folder."
    return render_template("forgot_password.html", message=message)

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    ensure_feature_schema()
    valid = password_reset_token_is_valid(token)
    error = None
    if request.method == "POST":
        if not valid:
            error = "This password reset link is invalid or has expired. Please request a new one."
        else:
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            if len(password) < 8:
                error = "Password must be at least 8 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            else:
                password_hash = generate_password_hash(password, method="pbkdf2:sha256")
                if reset_password_with_token(token, password_hash):
                    session.clear()
                    return redirect("/login?changed=1")
                error = "This password reset link is invalid or has expired. Please request a new one."
                valid = False
    return render_template("reset_password.html", token=token, valid=valid, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/accounts")
def accounts():
    user = get_current_user()
    if not user:
        return redirect("/login")
    return render_template("accounts.html", accounts=list_financial_accounts(user["id"]), connections=list_bank_connections(user["id"]), setu_configured=setu_configured(), message=request.args.get("message"), error=request.args.get("error"))


@app.route("/accounts/connect/india", methods=["POST"])
def connect_india_account():
    user = get_current_user()
    if not user:
        return redirect("/login")
    if not setu_configured():
        return redirect("/accounts?error=Indian bank connectivity is not activated yet. Complete Setu Account Aggregator onboarding and add the production credentials in Render.")
    mobile = request.form.get("mobile", "").strip()
    try:
        callback = request.url_root.rstrip("/") + "/accounts"
        consent = create_consent(mobile, callback)
        consent_id = consent.get("id") or consent.get("consentId")
        consent_url = consent.get("url") or consent.get("webviewUrl")
        if not consent_id or not consent_url:
            raise RuntimeError("Setu did not return a consent URL. Please check the Setu product configuration.")
        create_bank_connection(user["id"], "setu_aa", consent_id, "pending")
        return redirect(consent_url)
    except Exception as exc:
        app.logger.exception("Setu consent creation failed")
        return redirect("/accounts?error=" + requests.utils.quote(str(exc)[:240]))


@app.route("/accounts/sync/<consent_id>", methods=["POST"])
def sync_india_account(consent_id):
    user = get_current_user()
    if not user:
        return redirect("/login")
    connection = get_bank_connection(user["id"], consent_id)
    if not connection:
        return redirect("/accounts?error=Connection not found.")
    try:
        consent = get_consent(consent_id)
        status = str(consent.get("status", "")).upper()
        if status in {"REJECTED", "REVOKED", "EXPIRED", "PAUSED"}:
            update_bank_connection(user["id"], consent_id, status.lower())
            return redirect("/accounts?error=" + requests.utils.quote(f"Bank consent status is {status.lower()}"))
        if status not in {"ACTIVE", "APPROVED"}:
            update_bank_connection(user["id"], consent_id, status.lower() or "pending")
            return redirect("/accounts?message=Your bank consent is still waiting for approval or account data.")
        now = datetime.utcnow()
        start = datetime(now.year - 2, now.month, now.day).isoformat() + "Z"
        end = now.isoformat() + "Z"
        session_data = create_session(consent_id, start, end)
        session_id = session_data.get("id") or session_data.get("dataSessionId")
        update_bank_connection(user["id"], consent_id, "fetching", session_id)
        if not session_id:
            return redirect("/accounts?message=Bank connection started. Sigora is waiting for transaction data.")
        fetched = get_session(session_id)
        status2 = str(fetched.get("status", "")).upper()
        if status2 not in {"PARTIAL", "COMPLETED"}:
            return redirect("/accounts?message=Bank connection is waiting for the bank to provide transaction data. Try sync again shortly.")
        imported = 0
        parsed_accounts = parse_accounts(fetched)
        account_ids = []
        for item in parsed_accounts:
            account_ids.append(upsert_financial_account(user["id"], "setu_aa", item["institution_name"], item["account"], "India", item["currency"]))
        parsed = parse_transactions(fetched)
        for tx in parsed:
            result = import_external_transaction(user["id"], tx, account_ids[0] if account_ids else None)
            if result.get("created"):
                imported += 1
        update_bank_connection(user["id"], consent_id, "connected", session_id, True)
        return redirect("/accounts?message=" + requests.utils.quote(f"Bank sync complete. {imported} new transaction(s) imported."))
    except Exception as exc:
        app.logger.exception("Setu sync failed")
        return redirect("/accounts?error=" + requests.utils.quote(str(exc)[:240]))


@app.route("/webhooks/setu/aa", methods=["POST"])
def setu_aa_webhook():
    payload = request.get_json(silent=True) or {}
    consent_id = payload.get("consentId")
    if not consent_id:
        return jsonify({"success": True})

    connection = get_bank_connection_by_consent(consent_id)
    if not connection:
        # Unknown consent IDs are ignored and never create user data.
        return jsonify({"success": True})

    user_id = connection["user_id"]
    event_type = str(payload.get("type") or "").upper()
    status_raw = str((payload.get("data") or {}).get("status") or payload.get("status") or "pending").upper()
    update_bank_connection(user_id, consent_id, status_raw.lower())

    try:
        fetched = None
        data_session_id = payload.get("dataSessionId")

        # Current Setu Auto-Fetch can deliver decrypted FI data directly in the webhook.
        if event_type == "FI_DATA_READY" and payload.get("fiData"):
            fetched = payload
        # Standard data-session notifications require a follow-up authenticated fetch.
        elif event_type == "SESSION_STATUS_UPDATE" and status_raw in {"PARTIAL", "COMPLETED"} and data_session_id:
            fetched = get_session(data_session_id)

        if fetched:
            account_by_mask = {}
            first_account_id = None
            for item in parse_accounts(fetched):
                aid = upsert_financial_account(user_id, "setu_aa", item["institution_name"], item["account"], "India", item["currency"])
                if first_account_id is None:
                    first_account_id = aid
                masked = str(item["account"].get("maskedAccNumber") or "")
                if masked:
                    account_by_mask[masked] = aid

            for tx in parse_transactions(fetched):
                aid = account_by_mask.get(str(tx.get("account_masked") or ""), first_account_id)
                import_external_transaction(user_id, tx, aid)

            update_bank_connection(user_id, consent_id, "connected", data_session_id, True)
    except Exception:
        app.logger.exception("Automatic Setu transaction ingestion failed")

    return jsonify({"success": True})


@app.route("/settings", methods=["GET", "POST"])
def settings():
    user = get_current_user()
    if not user:
        return redirect("/login")

    settings_data = get_user_settings(user["id"])
    error = None

    if request.method == "POST":
        action = request.form.get("action", "preferences")

        if action == "preferences":
            name = request.form.get("name", "").strip()
            country = request.form.get("country", "India").strip()[:100]
            requested_currency = request.form.get("currency", "").strip().upper()[:10]
            allowed_currencies = {code for code, _symbol in COUNTRY_CURRENCIES.values()}
            if country in COUNTRY_CURRENCIES:
                currency = requested_currency or currency_for_country(country)[0]
            else:
                currency = requested_currency or "INR"

            if currency not in allowed_currencies:
                error = "Please select a supported currency."
            elif not name:
                error = "Name cannot be empty."
            else:
                try:
                    update_user_settings(
                        user["id"], name, currency, country or "India",
                        request.form.get("notification_email_enabled") == "on",
                        request.form.get("budget_alerts_enabled") == "on",
                        request.form.get("goal_alerts_enabled") == "on",
                        request.form.get("ai_alerts_enabled") == "on",
                    )
                    return redirect("/settings?saved=1")
                except RuntimeError as exc:
                    # FX availability should never produce the generic 500 page.
                    error = str(exc)

        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not check_user_password(current_password, user["password_hash"]):
                error = "Current password is incorrect."
            elif len(new_password) < 8:
                error = "New password must be at least 8 characters."
            elif new_password != confirm_password:
                error = "New passwords do not match."
            else:
                change_user_password(user["id"], generate_password_hash(new_password, method="pbkdf2:sha256"))
                session.clear()
                return redirect("/login?changed=1")

        elif action == "delete_account":
            delete_user_account(user["id"])
            session.clear()
            return redirect("/?deleted=1")

        elif action == "support":
            support_email = request.form.get("email", "").strip().lower()
            issue_type = request.form.get("issue_type", "General question").strip()
            message = request.form.get("message", "").strip()
            if not support_email or "@" not in support_email or not message:
                error = "Please enter a valid email and a message."
            else:
                submit_support_message(user["id"], settings_data["name"], support_email, issue_type, message)
                return redirect("/settings?support=sent")

    settings_data = get_user_settings(user["id"])
    return render_template("settings.html", settings=settings_data, premium_features=premium_features(), error=error)


@app.route("/alerts/<int:alert_id>/read", methods=["POST"])
def read_alert(alert_id):
    user = get_current_user()
    if not user:
        return redirect("/login")
    mark_alert_read(user["id"], alert_id)
    return redirect(request.form.get("next") or "/dashboard")


@app.route("/premium/subscribe", methods=["POST"])
def premium_subscribe():
    user = get_current_user()
    if not user:
        return redirect("/login")
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    pricing = get_pricing(user.get("currency", "INR"), user.get("country", "India"))
    plan_id = pricing.get("plan_id")
    coupon_code = request.form.get("coupon_code","").strip().upper()
    coupon = None
    if coupon_code:
        from product_features import validate_coupon
        coupon = validate_coupon(coupon_code, user["id"])
        if not coupon.get("valid"):
            return redirect("/premium?payment=coupon_error")
    if not all([key_id, key_secret, plan_id]):
        return redirect("/premium?payment=not_configured")
    try:
        subscription_payload = {
            "plan_id": plan_id,
            "total_count": int(os.getenv("RAZORPAY_TOTAL_COUNT", "120")),
            "customer_notify": True,
            "notes": {"user_id": str(user["id"]), "product": "Sigora Premium", "coupon_code": coupon_code or "", "billing_currency": pricing["currency"]},
        }
        if coupon and coupon.get("razorpay_offer_id"):
            subscription_payload["offer_id"] = coupon["razorpay_offer_id"]
        response = requests.post(
            "https://api.razorpay.com/v1/subscriptions",
            auth=(key_id, key_secret),
            json=subscription_payload,
            timeout=15,
        )
        if not response.ok:
            try:
                razorpay_error = response.json().get("error", {})
                error_code = razorpay_error.get("code", "unknown")
                error_description = razorpay_error.get("description", "Razorpay rejected the subscription request")
            except Exception:
                error_code = "unknown"
                error_description = "Razorpay rejected the subscription request"
            app.logger.error(
                "Razorpay subscription creation failed: status=%s code=%s description=%s",
                response.status_code, error_code, error_description
            )
            return redirect("/premium?payment=provider_error")
        data = response.json()
        subscription_id = data.get("id")
        if subscription_id and coupon:
            remember_subscription_coupon(subscription_id, coupon["id"], user["id"])
        if subscription_id:
            conn = get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET razorpay_subscription_id=%s WHERE id=%s", (subscription_id, user["id"]))
                conn.commit()
            finally:
                conn.close()
        return render_template("premium_checkout.html", key_id=key_id, subscription=data)
    except Exception as exc:
        print("RAZORPAY SUBSCRIPTION ERROR:", repr(exc))
        return redirect("/premium?payment=error")


@app.route("/razorpay/verify", methods=["POST"])
def razorpay_verify():
    user = get_current_user()
    if not user:
        return jsonify({"ok": False, "error": "Login required"}), 401
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    data = request.get_json(silent=True) or {}
    payment_id = data.get("razorpay_payment_id", "")
    subscription_id = data.get("razorpay_subscription_id", "")
    signature = data.get("razorpay_signature", "")
    if not all([key_secret, payment_id, subscription_id, signature]):
        return jsonify({"ok": False, "error": "Missing payment verification fields"}), 400
    expected = hmac.new(key_secret.encode(), f"{payment_id}|{subscription_id}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return jsonify({"ok": False, "error": "Invalid payment signature"}), 400
    if get_user_id_for_subscription(subscription_id) != user["id"]:
        return jsonify({"ok": False, "error": "Subscription does not belong to this account"}), 403
    return jsonify({"ok": True})


@app.route("/premium/cancel", methods=["POST"])
def premium_cancel():
    user = get_current_user()
    if not user:
        return redirect("/login")
    subscription_id = get_razorpay_subscription_id(user["id"])
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not all([subscription_id, key_id, key_secret]):
        return redirect("/premium?cancel=not_configured")
    try:
        response = requests.post(
            f"https://api.razorpay.com/v1/subscriptions/{subscription_id}/cancel",
            auth=(key_id, key_secret), json={"cancel_at_cycle_end": True}, timeout=15
        )
        response.raise_for_status()
        cancel_data = response.json() if response.content else {}
        cancel_end = None
        if cancel_data.get("current_end"):
            try:
                cancel_end = datetime.utcfromtimestamp(int(cancel_data["current_end"]))
            except (ValueError, TypeError, OSError):
                cancel_end = None
        # cancel_at_cycle_end stops renewal, not already-paid access.
        # Preserve the entitlement immediately from Razorpay's authoritative current_end.
        if cancel_end and cancel_end > datetime.utcnow():
            from product_features import set_premium_status
            set_premium_status(user["id"], True, cancel_end, cancel_data.get("status"))
        mark_subscription_cancellation_requested(user["id"], True)
        return redirect("/premium?cancel=requested")
    except Exception as exc:
        print("RAZORPAY CANCEL ERROR:", repr(exc))
        return redirect("/premium?cancel=error")


@app.route("/razorpay/webhook", methods=["POST"])
def razorpay_webhook():
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        return jsonify({"ok": False, "error": "Webhook secret not configured"}), 503
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return jsonify({"ok": False, "error": "Invalid signature"}), 400
    payload = request.get_json(silent=True) or {}
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    subscription_id = entity.get("id")
    notes = entity.get("notes") or {}
    user_id = notes.get("user_id") or (get_user_id_for_subscription(subscription_id) if subscription_id else None)
    if not user_id:
        return jsonify({"ok": True})
    active_events = {"subscription.activated", "subscription.charged"}
    # Razorpay can cancel at cycle end. A cancellation event must not remove
    # access before current_end if a paid period is still in progress.
    terminal_events = {"subscription.halted", "subscription.completed"}
    expires_at = None
    if entity.get("current_end"):
        try:
            expires_at = datetime.utcfromtimestamp(int(entity["current_end"]))
        except (ValueError, TypeError, OSError):
            expires_at = None
    if event in active_events:
        from product_features import set_premium_status
        set_premium_status(int(user_id), True, expires_at, entity.get("status"))
        if event == "subscription.activated":
            mark_subscription_cancellation_requested(int(user_id), False)
        if subscription_id:
            redeem_subscription_coupon(subscription_id)
    elif event == "subscription.cancelled":
        from product_features import set_premium_status
        if expires_at and expires_at > datetime.utcnow():
            set_premium_status(int(user_id), True, expires_at, entity.get("status"))
            mark_subscription_cancellation_requested(int(user_id), True)
        else:
            set_premium_status(int(user_id), False, expires_at, entity.get("status"))
    elif event in terminal_events:
        from product_features import set_premium_status
        set_premium_status(int(user_id), False, expires_at, entity.get("status"))
    return jsonify({"ok": True})


@app.route("/privacy")
def privacy_policy():
    return render_template("privacy.html")

@app.route("/terms")
def terms_of_service():
    return render_template("terms.html")

@app.route("/financial-disclaimer")
def financial_disclaimer():
    return render_template("financial_disclaimer.html")

@app.route("/support")
def support_page():
    return render_template("support.html")

@app.route("/intelligence", methods=["GET", "POST"])
def intelligence():
    user = get_current_user()
    if not user:
        return redirect("/login")
    status = get_premium_status(user["id"])
    context = get_ai_financial_context(user["id"])
    month, year = datetime.now().month, datetime.now().year
    budgets_data = get_budgets(user["id"], month, year)
    for b in budgets_data:
        b["spent"] = get_budget_spending(user["id"], b["category"], month, year)
    goals_data = get_goals(user["id"])
    result = build_intelligence(context, budgets_data, goals_data)
    simulation = None
    if request.method == "POST":
        if not status["is_premium"]:
            return redirect("/premium")
        try:
            amount = float(request.form.get("purchase_amount", "0"))
        except ValueError:
            amount = 0
        simulation = simulate_purchase(context, amount, goals_data)
    return render_template("intelligence.html", intelligence=result, simulation=simulation, is_premium=status["is_premium"])

@app.route("/premium")
def premium():
    user = get_current_user()
    if not user:
        return redirect("/login")
    settings_data = get_user_settings(user["id"])
    status = get_premium_status(user["id"])
    usage = get_ai_usage(user["id"])
    ai_limits = get_ai_limits(status["is_premium"])
    pricing = get_pricing(user.get("currency", "INR"), user.get("country", "India"))
    context = get_ai_financial_context(user["id"])
    month, year = datetime.now().month, datetime.now().year
    intel_budgets = get_budgets(user["id"], month, year)
    for b in intel_budgets:
        b["spent"] = get_budget_spending(user["id"], b["category"], month, year)
    intelligence = build_intelligence(context, intel_budgets, get_goals(user["id"]))
    payment_ready = bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET") and pricing.get("plan_id"))
    return render_template("premium.html", settings=settings_data, premium_features=premium_features(intelligence), premium_status=status, ai_usage=usage, ai_limits=ai_limits, payment_ready=payment_ready, pricing=pricing, intelligence=intelligence)

@app.route("/admin/coupons", methods=["GET","POST"])
def admin_coupons():
    user=get_current_user()
    if not user or not os.getenv("ADMIN_EMAIL") or user.get("email","").lower()!=os.getenv("ADMIN_EMAIL","").lower():
        return "Not found",404
    ensure_monetization_schema()
    if request.method=="POST":
        action=request.form.get("action")
        try:
            if action=="create":
                create_coupon(
                    request.form.get("code",""),
                    request.form.get("discount_type","percent"),
                    float(request.form.get("discount_value","0")),
                    int(request.form["max_uses"]) if request.form.get("max_uses") else None,
                    request.form.get("valid_until") or None,
                    request.form.get("first_month_only")=="on",
                    request.form.get("razorpay_offer_id","").strip() or None
                )
            elif action=="toggle":
                toggle_coupon(int(request.form["coupon_id"]), request.form.get("active")=="1")
        except Exception as exc:
            print("COUPON ADMIN ERROR:",repr(exc))
    return render_template("admin_coupons.html", coupons=list_coupons(), premium_price=get_pricing()["premium_price"])

def get_current_user():
    ensure_feature_schema()
    user_id = session.get("user_id")

    if not user_id:
        return None

    return get_user_by_id(user_id)

def categorize_transaction(description, transaction_type):
    """
    Automatically categorizes a transaction
    based on its description.
    """

    description = description.lower().strip()

    # -----------------------------
    # INCOME CATEGORIES
    # -----------------------------

    if transaction_type == "income":

        if any(word in description for word in [
            "salary",
            "payroll",
            "salary credit"
        ]):
            return "Salary"

        if any(word in description for word in [
            "freelance",
            "freelancer",
            "consulting",
            "consultation"
        ]):
            return "Freelance"

        if any(word in description for word in [
            "interest",
            "bank interest"
        ]):
            return "Interest"

        if any(word in description for word in [
            "refund",
            "cashback",
            "cash back"
        ]):
            return "Refund"

        return "Other Income"


    # -----------------------------
    # EXPENSE CATEGORIES
    # -----------------------------

    if transaction_type == "expense":

        # Food
        if any(word in description for word in [
            "swiggy",
            "zomato",
            "dominos",
            "pizza",
            "mcdonald",
            "kfc",
            "restaurant",
            "cafe",
            "food"
        ]):
            return "Food"

        # Shopping
        if any(word in description for word in [
            "amazon",
            "flipkart",
            "myntra",
            "ajio",
            "shopping",
            "mall",
            "retail"
        ]):
            return "Shopping"

        # Transport
        if any(word in description for word in [
            "uber",
            "ola",
            "rapido",
            "metro",
            "bus",
            "train",
            "transport"
        ]):
            return "Transport"

        # Fuel
        if any(word in description for word in [
            "petrol",
            "fuel",
            "diesel",
            "hpcl",
            "bpcl",
            "iocl"
        ]):
            return "Fuel"

        # Entertainment
        if any(word in description for word in [
            "netflix",
            "spotify",
            "prime video",
            "hotstar",
            "youtube",
            "movie",
            "cinema",
            "entertainment"
        ]):
            return "Entertainment"

        # Utilities
        if any(word in description for word in [
            "electricity",
            "eb bill",
            "water bill",
            "gas bill",
            "broadband",
            "internet",
            "wifi",
            "mobile recharge",
            "recharge"
        ]):
            return "Utilities"

        # Housing
        if any(word in description for word in [
            "rent",
            "maintenance",
            "housing",
            "apartment"
        ]):
            return "Housing"

        # Healthcare
        if any(word in description for word in [
            "hospital",
            "doctor",
            "pharmacy",
            "medical",
            "medicine",
            "apollo",
            "healthcare"
        ]):
            return "Healthcare"

        # Insurance
        if any(word in description for word in [
            "insurance",
            "lic premium",
            "policy premium"
        ]):
            return "Insurance"

        # Education
        if any(word in description for word in [
            "college",
            "school",
            "tuition",
            "course",
            "udemy",
            "coursera",
            "education"
        ]):
            return "Education"

        # Travel
        if any(word in description for word in [
            "flight",
            "airline",
            "hotel",
            "booking",
            "travel",
            "airbnb"
        ]):
            return "Travel"

        return "Uncategorized"

    return "Uncategorized"

@app.route("/import-transactions", methods=["GET", "POST"])
def import_transactions():
    user = get_current_user()
    if not user:
        return redirect("/login")
    if request.method == "GET":
        return render_template("import_transactions.html")

    file = request.files.get("file")
    if not file or not file.filename:
        return render_template("import_transactions.html", error="Please select a statement file.")

    max_mb = int(os.getenv("IMPORT_MAX_FILE_MB", "25"))
    if request.content_length and request.content_length > max_mb * 1024 * 1024:
        return render_template("import_transactions.html", error=f"That file is larger than the {max_mb} MB import limit.")

    password = request.form.get("pdf_password") or None
    try:
        rows, columns, detected_format = read_statement(file, file.filename, password=password)
        normalized, errors = normalize_rows(rows, columns, categorize_transaction)
    except ValueError as exc:
        msg = str(exc)
        if msg == "PDF_PASSWORD_REQUIRED":
            return render_template("import_transactions.html", error="This PDF is password protected. Enter its PDF password to continue.", password_required=True)
        if msg == "PDF_PASSWORD_INVALID":
            return render_template("import_transactions.html", error="That PDF password is incorrect. Please try again.", password_required=True)
        return render_template("import_transactions.html", error=msg, password_required=detected_format if 'detected_format' in locals() else False)
    except Exception as exc:
        print("IMPORT ERROR:", repr(exc))
        return render_template("import_transactions.html", error="Sigora couldn't read that statement safely. Please check the file and try again.")

    # Remove duplicates inside the uploaded statement.
    unique, seen = [], set()
    for t in normalized:
        key=(t["date"], t["description"].strip().lower(), t["transaction_type"], round(float(t["amount"]),2))
        if key not in seen:
            seen.add(key); unique.append(t)
    normalized=unique

    candidates=[(t["date"],t["description"],t["transaction_type"],t["amount"]) for t in normalized]
    existing=find_existing_transaction_keys(user["id"], candidates)
    importable=[t for t in normalized if (t["date"],t["description"].strip().lower(),t["transaction_type"],round(float(t["amount"]),2)) not in existing]
    skipped=len(normalized)-len(importable)

    if request.form.get("confirm") == "1":
        count=batch_add_transactions(user["id"], [dict(t,source="import",currency=user.get("currency","INR")) for t in importable])
        if count:
            award_activity(user["id"], "transaction", min(50,count))
        return render_template("import_transactions.html", success=True, imported_count=count, skipped_count=skipped, error_count=len(errors), errors=errors)

    return render_template("import_transactions.html", preview=True, preview_rows=importable[:200], total_found=len(normalized), importable_count=len(importable), skipped_count=skipped, error_count=len(errors), errors=errors[:20], original_filename=file.filename, detected_format=detected_format, password_required=bool(detected_format == "pdf" and password))





def _market_search(query):
    """Resolve a company/fund name or ticker using Yahoo Finance public search."""
    try:
        r=requests.get("https://query1.finance.yahoo.com/v1/finance/search", params={"q":query,"quotesCount":8,"newsCount":0}, headers={"User-Agent":"Mozilla/5.0"}, timeout=6)
        r.raise_for_status()
        out=[]
        for q in r.json().get("quotes",[]):
            if q.get("symbol") and q.get("quoteType") in {"EQUITY","ETF","MUTUALFUND","INDEX"}:
                out.append({"symbol":q.get("symbol"),"name":q.get("longname") or q.get("shortname") or q.get("symbol"),"exchange":q.get("exchDisp") or q.get("exchange") or "", "type":q.get("quoteType","")})
        return out
    except Exception:
        return []

def _market_chart(symbol, range_="1mo", interval="1d"):
    """Fetch market metadata plus a real historical series; never fabricate chart points."""
    try:
        def fetch_chart(fetch_symbol):
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{fetch_symbol}",
                params={"range": range_, "interval": interval},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=6,
            )
            r.raise_for_status()
            result = (r.json().get("chart", {}).get("result") or [None])[0]
            if not result:
                return None, []
            ts = result.get("timestamp", [])
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            closes = quote.get("close", [])
            points = [{"t": t, "v": v} for t, v in zip(ts, closes) if v is not None]
            return result, points

        result, points = fetch_chart(symbol)
        if not result:
            return None
        meta = result.get("meta", {})

        # A two-point multi-month chart is misleading: Chart.js renders it as a
        # perfect diagonal. BSE history can be sparse on Yahoo, so use the same
        # company's NSE listing for HISTORY only when the BSE series is sparse.
        min_points = {"5d": 3, "1mo": 5, "6mo": 20, "1y": 30, "5y": 30}.get(range_, 3)
        if len(points) < min_points and symbol.upper().endswith(".BO"):
            fallback_symbol = symbol[:-3] + ".NS"
            try:
                _, fallback_points = fetch_chart(fallback_symbol)
                if len(fallback_points) >= min_points:
                    points = fallback_points
            except Exception:
                pass

        # Do not draw a fake-looking straight trend from only one/two sparse
        # observations. The UI will clearly report unavailable history instead.
        if len(points) < 3:
            points = []

        price = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        change = (price - prev) if price is not None and prev else None
        pct = (change / prev * 100) if change is not None and prev else None
        return {
            "symbol": symbol, "name": meta.get("longName") or meta.get("shortName") or symbol,
            "exchange": meta.get("exchangeName") or meta.get("fullExchangeName") or "",
            "currency": meta.get("currency") or "", "price": price, "previous_close": prev,
            "change": change, "change_pct": pct, "day_high": meta.get("regularMarketDayHigh"),
            "day_low": meta.get("regularMarketDayLow"), "fifty_two_high": meta.get("fiftyTwoWeekHigh"),
            "fifty_two_low": meta.get("fiftyTwoWeekLow"), "points": points,
        }
    except Exception:
        return None

def _plain_market_explanation(m):
    if not m or m.get("price") is None: return "Live market data is temporarily unavailable. Try again shortly."
    pct=m.get("change_pct")
    if pct is None: tone="The latest price is available, but today's comparison is unavailable."
    elif pct >= 2: tone=f"The price is up {pct:.2f}% today — a noticeable positive move for one session."
    elif pct > 0: tone=f"The price is up {pct:.2f}% today — a modest positive move."
    elif pct <= -2: tone=f"The price is down {abs(pct):.2f}% today — a noticeable decline for one session."
    elif pct < 0: tone=f"The price is down {abs(pct):.2f}% today — a modest decline."
    else: tone="The price is roughly unchanged today."
    pts=m.get("points") or []
    if len(pts)>1 and pts[0]["v"]:
        period=(pts[-1]["v"]/pts[0]["v"]-1)*100
        trend=f" Over the displayed period it has {'risen' if period>=0 else 'fallen'} about {abs(period):.1f}%."
    else: trend=""
    return tone+trend+" Short-term price moves do not tell you whether an investment is suitable; look at the business/fund, diversification, time horizon and risk as well."

@app.route("/invest")
def invest():
    user=get_current_user()
    if not user: return redirect("/login")
    profile=get_profile(user["id"])
    portfolio=portfolio_summary(user["id"])
    cashflow=financial_investment_context(user["id"], profile)
    allocation=model_allocation(profile["profile"]) if profile else None
    watchlist=get_watchlist(user["id"])
    for item in watchlist:
        item["market"]=_market_chart(item.get("symbol"), "5d", "1d") if item.get("symbol") else None
    return render_template("invest.html", profile=profile, portfolio=portfolio, cashflow=cashflow, allocation=allocation, watchlist=watchlist, explorer=EXPLORER)

@app.route("/invest/profile", methods=["GET","POST"])
def investment_profile():
    user=get_current_user()
    if not user: return redirect("/login")
    if request.method == "POST":
        try:
            save_profile(user["id"], request.form.get("objective","growth"), int(request.form.get("horizon_years",5)), request.form.get("risk_comfort","moderate"), request.form.get("loss_reaction","hold"), float(request.form.get("emergency_months",0) or 0), float(request.form.get("monthly_investment",0) or 0))
            flash("Investor profile updated.", "success")
            return redirect("/invest")
        except ValueError:
            flash("Please enter valid numbers.", "danger")
    return render_template("investment_profile.html", profile=get_profile(user["id"]))

@app.route("/invest/holding/add", methods=["POST"])
def investment_add():
    user=get_current_user()
    if not user: return redirect("/login")
    try:
        add_investment(user["id"], request.form.get("name","").strip(), request.form.get("symbol","").strip().upper(), request.form.get("asset_type","Stock"), request.form.get("sector","").strip(), float(request.form.get("quantity",0)), float(request.form.get("average_cost",0)), float(request.form.get("current_price",0)), user.get("currency","INR"), request.form.get("notes","").strip())
        flash("Investment added to your tracker.", "success")
    except (ValueError, TypeError): flash("Please enter valid investment values.", "danger")
    return redirect("/invest")

@app.route("/invest/holding/<int:investment_id>/price", methods=["POST"])
def investment_price(investment_id):
    user=get_current_user()
    if not user: return redirect("/login")
    try: update_investment_price(user["id"], investment_id, float(request.form.get("current_price",0)))
    except ValueError: flash("Please enter a valid price.", "danger")
    return redirect("/invest")

@app.route("/invest/holding/<int:investment_id>/delete", methods=["POST"])
def investment_delete(investment_id):
    user=get_current_user()
    if not user: return redirect("/login")
    delete_investment(user["id"], investment_id); flash("Investment removed.", "success")
    return redirect("/invest")

@app.route("/invest/watchlist/add", methods=["POST"])
def investment_watchlist_add():
    user=get_current_user()
    if not user: return redirect("/login")
    query=request.form.get("name","").strip()
    if query:
        matches=_market_search(query)
        chosen=matches[0] if matches else None
        if chosen:
            add_watchlist(user["id"], chosen["name"], chosen["symbol"], chosen.get("type") or "Stock", request.form.get("note","").strip())
            flash(f"{chosen['name']} added to your watchlist.", "success")
        else:
            flash("We couldn't find that investment. Try the company name or ticker (for example Reliance, AAPL or MSFT).", "danger")
    return redirect("/invest")

@app.route("/invest/watchlist/<int:item_id>/delete", methods=["POST"])
def investment_watchlist_delete(item_id):
    user=get_current_user()
    if not user: return redirect("/login")
    delete_watchlist(user["id"],item_id); return redirect("/invest")

@app.route("/invest/ai", methods=["POST"])
def investment_ai():
    user=get_current_user()
    if not user: return redirect("/login")
    profile=get_profile(user["id"]); portfolio=portfolio_summary(user["id"]); cashflow=financial_investment_context(user["id"],profile)
    context={"profile":profile,"portfolio":portfolio,"cashflow":cashflow,"model_allocation":model_allocation(profile["profile"]) if profile else None}
    ai_result=run_limited_ai(user["id"], get_investment_ai_insight, context)
    return render_template("investment_ai.html", ai_result=ai_result, profile=profile, portfolio=portfolio)


@app.route("/invest/market/<path:symbol>")
def investment_market_detail(symbol):
    user=get_current_user()
    if not user: return redirect("/login")
    period=request.args.get("period","1mo")
    allowed={"5d":("5d","30m"),"1mo":("1mo","1d"),"6mo":("6mo","1d"),"1y":("1y","1d"),"5y":("5y","1wk")}
    rng,interval=allowed.get(period,allowed["1mo"])
    market=_market_chart(symbol,rng,interval)
    explanation=_plain_market_explanation(market)
    return render_template("investment_market.html", market=market, symbol=symbol, period=period, explanation=explanation)

@app.route("/insights")
def insights():
    user = get_current_user()
    if not user:
        return redirect("/login")
    context = get_ai_financial_context(user["id"])
    ai_result = run_limited_ai(user["id"], get_ai_insights, context)
    status = get_premium_status(user["id"])
    usage = get_ai_usage(user["id"])
    ai_limits = get_ai_limits(status["is_premium"])
    return render_template("insights.html", ai_result=ai_result, is_premium=status["is_premium"], usage=usage, monthly_limit=ai_limits["monthly"], daily_limit=ai_limits["daily"])

@app.errorhandler(413)
def request_too_large(error):
    return render_template("import_transactions.html", error=f"That upload is too large. The maximum statement size is {os.getenv('IMPORT_MAX_FILE_MB', '25')} MB."), 413

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug)
