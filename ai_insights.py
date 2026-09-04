import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


# =====================================================
# AI FALLBACK
# =====================================================

AI_UNAVAILABLE_MESSAGE = (
    "Sigora AI is temporarily unavailable. "
    "Your financial data is still being tracked normally."
)


# =====================================================
# GEMINI CLIENT
# =====================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
AI_ENABLED = os.getenv("AI_ENABLED", "1") == "1"

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# =====================================================
# AI PROVIDER
# =====================================================

AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


def _generate(prompt, label):
    """Generate AI text while keeping the finance app usable if AI fails."""
    if not AI_ENABLED:
        return AI_UNAVAILABLE_MESSAGE

    try:
        if AI_PROVIDER == "ollama":
            import requests

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "").strip()

            if text:
                return text

            print(f"{label}: Ollama returned no text.")
            return AI_UNAVAILABLE_MESSAGE

        if client is None:
            print(f"{label}: GEMINI_API_KEY is not configured.")
            return AI_UNAVAILABLE_MESSAGE

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        if not response or not response.text:
            return AI_UNAVAILABLE_MESSAGE

        return response.text.strip()

    except Exception as e:
        error_text = repr(e)
        print(f"{label}:", error_text)
        if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower() or "rate limit" in error_text.lower():
            return "Sigora AI is temporarily rate-limited. Please try again shortly. Your financial data is safe and unchanged."
        return AI_UNAVAILABLE_MESSAGE


# =====================================================
# GENERAL AI INSIGHTS
# =====================================================

def get_ai_insights(financial_context):

    prompt = f"""
You are Sigora AI, a personal finance insights assistant.

Analyze the user's financial data below.

USER FINANCIAL DATA:

{financial_context}


IMPORTANT RULES:

- Only use the information provided.
- Never invent amounts, transactions, percentages, or trends.
- Do not simply repeat the numbers.
- Explain why a pattern matters.
- If there is insufficient data, say so.
- Do not provide investment, tax, legal, medical,
  or other regulated financial advice.
- Keep the language simple and conversational.
- Focus on the most important insights.


Return EXACTLY these sections:

## 💰 Savings Insight

Explain the user's current savings position.

## 📊 Spending Pattern

Identify the most important spending pattern.

## ⚠️ Attention

Identify one thing that deserves attention.

## 💡 Recommendation

Give ONE practical action based on the data.

## 🎯 Positive Habit

Identify ONE thing the user is doing well.

Keep each section concise.
"""

    return _generate(prompt, "GEMINI AI ERROR")


# =====================================================
# GOAL AI
# =====================================================

def get_goal_ai_insight(
    goal,
    expense_categories
):

    if expense_categories:

        spending_text = "\n".join(
            [
                f'- {item["category"]}: '
                f'₹{item["total"]:.2f}'
                for item in expense_categories
            ]
        )

    else:

        spending_text = (
            "No expense category data available."
        )


    prompt = f"""
You are Sigora AI, a personal finance assistant.

Help the user realistically reach their financial goal.

GOAL INFORMATION:

Goal name:
{goal["name"]}

Target amount:
₹{goal["target_amount"]:.2f}

Current amount saved:
₹{goal["current_amount"]:.2f}

Remaining:
₹{goal["remaining"]:.2f}

Target date:
{goal["target_date"]}

Required monthly saving:
₹{goal["required_monthly_saving"]:.2f}

Recent average monthly saving:
₹{goal["average_monthly_saving"]:.2f}

Likelihood:
{goal["likelihood"]}


USER'S ACTUAL EXPENSE CATEGORIES:

{spending_text}


YOUR JOB:

Do NOT simply tell the user how much they need to save.

Instead, use the actual expense information to suggest
realistic ways the user could improve their ability
to reach the goal.

Consider:

- Which expense categories are the largest.
- Which categories may be worth reviewing.
- Whether discretionary spending could be adjusted.
- Whether existing savings could be redirected.
- Whether the user is already comfortably on track.
- Whether additional income is genuinely useful.
- If additional income is useful, suggest ONE flexible,
  optional side-income idea.
- Include a short precaution when suggesting extra income.
- Protect essential living expenses.
- Never recommend extreme cost cutting.


IMPORTANT RULES:

- Only use the information provided above.
- Never invent spending categories.
- Never invent amounts.
- Never invent income.
- Never assume a large category is unnecessary.
- Use "consider reviewing" rather than telling the user
  to eliminate a category.
- Do not give investment, tax, legal, medical,
  or regulated financial advice.
- Do not recommend taking on debt.
- Do not guarantee side income.
- Extra income must always be optional.
- If the user is comfortably on track, do not push
  them toward extra work.
- Be encouraging but honest.
- Keep the response under 160 words.


RETURN EXACTLY:

MAIN INSIGHT:
2-3 concise sentences explaining the user's situation
and the most useful overall strategy.

SPENDING MOVE:
One specific spending category to consider reviewing.
Use the actual category and amount when useful.

SAVING MOVE:
One practical way to improve or redirect savings.

EXTRA INCOME:
If additional income is genuinely useful, suggest ONE
flexible optional income idea and briefly mention ONE
precaution.

If additional income is not necessary, write:

Not needed right now.
"""


    return _generate(prompt, "GOAL AI ERROR")


# =====================================================
# BUDGET AI
# =====================================================

def get_budget_ai_insight(
    budget,
    expense_categories
):

    if expense_categories:

        spending_text = "\n".join(
            [
                f'- {item["category"]}: ₹{item["total"]:.2f}'
                for item in expense_categories
            ]
        )

    else:

        spending_text = (
            "No expense category data available."
        )


    prompt = f"""
You are Sigora AI, a real-time personal finance
spending copilot.

Your job is to help the user make a smart decision
about their CURRENT monthly budget.

CURRENT BUDGET

Category:
{budget["category"]}

Monthly budget:
₹{budget["amount"]:.2f}

Spent:
₹{budget["spent"]:.2f}

Remaining:
₹{budget["remaining"]:.2f}

Percentage used:
{budget["percentage_used"]:.1f}%

Status:
{budget["status"]}

Month:
{budget["month"]}/{budget["year"]}


USER'S EXPENSE CATEGORIES

{spending_text}


IMPORTANT RULES

- Only use information provided above.
- Never invent transactions or amounts.
- Never assume an expense is unnecessary.
- Protect essential spending.
- Do not recommend extreme cost cutting.
- Do not recommend debt.
- Do not give investment, tax, legal, medical,
  or regulated financial advice.
- Do not guarantee extra income.
- Extra income should only be mentioned when
  there is a meaningful shortfall.
- If the budget is healthy, do not create
  unnecessary problems.
- Keep the advice practical and encouraging.
- Do not simply repeat the numbers.


YOUR RESPONSE MUST BE UNDER 90 WORDS.


RETURN EXACTLY:

STATUS:
Choose exactly ONE:
ON TRACK
WATCH
OVER BUDGET

HEADLINE:
One short sentence describing the situation.

ACTION:
One practical action the user can take right now.

DETAIL:
One short explanation of why this action makes sense.

EXTRA:
Only include an optional extra-income suggestion
if the budget situation genuinely requires it.

Otherwise write:
Not needed right now.
"""


    return _generate(prompt, "BUDGET AI ERROR")


# =====================================================
# DASHBOARD AI
# =====================================================

def get_dashboard_ai_insight(financial_context):

    prompt = f"""
You are Sigora AI, a personal finance assistant.

Analyze the user's financial dashboard data below.

USER FINANCIAL DATA:

{financial_context}


IMPORTANT RULES:

- Only use the information provided.
- Never invent amounts, transactions, percentages,
  categories, or trends.
- Do not simply repeat the numbers.
- Explain why the most important pattern matters.
- Be encouraging but honest.
- If there is insufficient data, say so.
- Do not provide investment, tax, legal, medical,
  or regulated financial advice.
- Do not recommend debt.
- Do not recommend extreme spending cuts.
- Keep the language simple and conversational.


Give the user a concise financial overview.

Focus on:

- Current financial position.
- Income versus expenses.
- The most important spending pattern.
- One practical area to pay attention to.
- One positive observation when supported by the data.

Keep the response concise.
"""

    return _generate(prompt, "DASHBOARD AI ERROR")

# =====================================================
# INVESTMENT AI — ANALYTICS / EDUCATION ONLY
# =====================================================
def get_investment_ai_insight(investment_context):
    prompt = f"""
You are Sigora Investment Intelligence, an educational portfolio analytics assistant.

DATA:
{investment_context}

STRICT SAFETY / PRODUCT RULES:
- Analyze only the supplied data.
- Do NOT tell the user to buy, sell, hold, switch, or allocate money to a named stock, fund, ETF, bond, crypto asset, or security.
- Do NOT provide target prices, return guarantees, timing calls, or personalized security recommendations.
- You MAY explain diversification, concentration, liquidity, volatility, cash-flow readiness, time horizon and educational model asset allocation.
- You MAY point out that a user's selected contribution exceeds their tracked surplus or that emergency liquidity appears low.
- Clearly distinguish tracked facts from educational examples.
- Never invent market prices or performance.
- Keep this under 220 words.

Return EXACTLY:
## Portfolio snapshot
2 concise sentences.

## Diversification check
1-3 concise observations based on actual tracked allocation/concentration.

## Financial readiness
1-2 concise observations connecting cash flow/emergency liquidity to investing.

## Risk-profile lens
Explain what the user's selected profile generally means, without recommending securities.

## One next step
ONE non-security-specific action such as reviewing concentration, updating prices, building liquidity, learning about an asset class, or comparing fees/risk.

End with: Educational analysis only — not a personalized investment recommendation.
"""
    return _generate(prompt, "INVESTMENT AI ERROR")

# =====================================================
# WHAT-IF V2 · NATURAL-LANGUAGE SCENARIO PARSER
# =====================================================

def parse_what_if_question(question, language="en"):
    """Turn a natural-language money question into structured inputs only.

    The model is deliberately NOT asked to decide affordability or do the
    financial maths. Those calculations remain in Sigora's deterministic
    financial engine.
    """
    import json
    import re

    question = (question or "").strip()
    if not question:
        return {"intent": "purchase", "subject": "this purchase", "amount": None, "timeframe": None}

    language_names = {"en": "English", "ta": "Tamil", "hi": "Hindi"}
    prompt = f"""
You are the intent parser for Sigora's What-If financial simulator.
The user's interface language is {language_names.get(language, 'English')}.

USER QUESTION:
{question}

Extract facts stated by the user. Never invent a price, amount, date, salary,
return, or other financial value. In particular, if the user names a product
such as an iPhone but gives no price, amount MUST be null.

Return ONLY valid JSON with these keys:
{{"intent":"purchase|recurring_expense|income_change|investment|other","subject":"short description in the user's language","amount":number_or_null,"timeframe":"short timeframe stated by user or null"}}

For recurring amounts, amount is the stated recurring amount. Do not calculate affordability.
"""
    raw = _generate(prompt, "What-if parser")
    if raw and raw != AI_UNAVAILABLE_MESSAGE and not raw.startswith("Sigora AI is temporarily"):
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I | re.S)
            data = json.loads(cleaned)
            amount = data.get("amount")
            try:
                amount = float(amount) if amount is not None else None
            except (TypeError, ValueError):
                amount = None
            return {
                "intent": str(data.get("intent") or "purchase"),
                "subject": str(data.get("subject") or question)[:160],
                "amount": amount if amount and amount > 0 else None,
                "timeframe": data.get("timeframe"),
            }
        except Exception as exc:
            print("What-if parser JSON fallback:", repr(exc))

    # Offline/no-AI fallback: extract an explicitly typed amount, never a product price.
    normalized = question.replace(",", "")
    patterns = [
        r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)\s*([kKlL]?)",
        r"(\d+(?:\.\d+)?)\s*([kKlL])(?:\b|akh)",
    ]
    amount = None
    for pattern in patterns:
        match = re.search(pattern, normalized, re.I)
        if match:
            amount = float(match.group(1))
            suffix = (match.group(2) or "").lower()
            if suffix == "k": amount *= 1000
            elif suffix == "l": amount *= 100000
            break
    return {"intent": "purchase", "subject": question[:160], "amount": amount, "timeframe": None}
