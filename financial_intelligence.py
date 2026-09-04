"""Deterministic Sigora Financial Intelligence.

Forecasts and scores are calculated from recorded user data, not invented by an LLM.
The AI layer may explain these signals, but these functions remain the source of truth.
"""
from calendar import monthrange
from datetime import date


def _f(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def build_intelligence(context, budgets=None, goals=None):
    """Build explainable financial signals only from data the user has recorded.

    A brand-new account must never receive a fabricated neutral health score.  When
    there is no transaction history we return an explicit insufficient-data state.
    Components are also included only when the underlying signal exists.
    """
    budgets = budgets or []
    goals = goals or []
    overall = context.get("overall") or {}
    latest = context.get("latest_month") or {}
    monthly_history = context.get("monthly_history") or []
    history = context.get("monthly_savings_history") or []

    total_income = _f(overall.get("total_income"))
    total_expense = _f(overall.get("total_expense"))
    has_financial_activity = bool(monthly_history) or total_income > 0 or total_expense > 0

    score_parts = {}

    # Savings is meaningful only when income has actually been recorded.
    if total_income > 0:
        savings_rate = _f(overall.get("savings_rate"))
        score_parts["Savings"] = _clamp(50 + savings_rate * 1.5)

    # Do not award a perfect budget score to an empty account. Budget adherence
    # becomes meaningful only after the user has recorded financial activity.
    if has_financial_activity and budgets:
        ratios = []
        for b in budgets:
            amount, spent = _f(b.get("amount")), _f(b.get("spent"))
            if amount > 0:
                ratios.append(spent / amount)
        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            score_parts["Budgets"] = _clamp(100 - max(0, avg_ratio - .70) * 140)

    # Goal progress is only scored when a valid goal contains actual recorded
    # progress. Merely creating a goal should not manufacture a neutral score.
    goal_progress = []
    for g in goals:
        target = _f(g.get("target_amount"))
        current = _f(g.get("current_amount"))
        if target > 0 and current > 0:
            goal_progress.append(_clamp(current / target * 100))
    if has_financial_activity and goal_progress:
        score_parts["Goals"] = _clamp(50 + (sum(goal_progress) / len(goal_progress)) * .5)

    # Stability requires at least two months; otherwise there is no trend to grade.
    monthly_savings = [_f(m.get("savings")) for m in history[-4:]]
    if len(monthly_savings) >= 2:
        mean = sum(monthly_savings) / len(monthly_savings)
        spread = sum(abs(x - mean) for x in monthly_savings) / len(monthly_savings)
        stability = 100 if abs(mean) < 1 and spread < 1 else _clamp(
            100 - (spread / max(abs(mean), 1)) * 55
        )
        score_parts["Stability"] = stability

    score_available = has_financial_activity and bool(score_parts)
    score = round(sum(score_parts.values()) / len(score_parts)) if score_available else None

    today = date.today()
    days_in_month = monthrange(today.year, today.month)[1]
    elapsed = max(today.day, 1)
    remaining_days = max(days_in_month - elapsed, 0)

    # A month-end forecast is valid only for data belonging to the current month.
    latest_is_current_month = bool(latest) and (
        int(latest.get("year", 0) or 0) == today.year
        and int(latest.get("month", 0) or 0) == today.month
    )
    latest_expense = _f(latest.get("expense")) if latest_is_current_month else 0
    latest_income = _f(latest.get("income")) if latest_is_current_month else 0
    forecast_available = latest_is_current_month and (latest_expense > 0 or latest_income > 0)

    projected_expense = None
    projected_savings = None
    if forecast_available:
        projected_expense = latest_expense / elapsed * days_in_month if latest_expense > 0 else 0.0
        if latest_income > 0:
            projected_savings = latest_income - projected_expense

    risks = []
    if forecast_available:
        for b in budgets:
            amount, spent = _f(b.get("amount")), _f(b.get("spent"))
            if amount <= 0 or spent <= 0:
                continue
            projected = spent / elapsed * days_in_month
            if projected > amount:
                allowance = max(amount - spent, 0)
                daily = allowance / remaining_days if remaining_days else 0
                risks.append({
                    "category": str(b.get("category") or "Budget").title(),
                    "budget": amount,
                    "spent": spent,
                    "projected": projected,
                    "over_by": projected - amount,
                    "days_remaining": remaining_days,
                    "daily_allowance": daily,
                    "severity": "high" if spent >= amount else "medium",
                })
    risks.sort(key=lambda r: r["over_by"], reverse=True)

    signal_count = len(score_parts)
    if not has_financial_activity:
        confidence = "not_ready"
    elif signal_count <= 1 or len(monthly_history) <= 1:
        confidence = "early"
    elif signal_count <= 2 or len(monthly_history) <= 2:
        confidence = "growing"
    else:
        confidence = "established"

    return {
        "score": score,
        "score_available": score_available,
        "score_parts": {k: round(v) for k, v in score_parts.items()},
        "has_financial_activity": has_financial_activity,
        "forecast_available": forecast_available,
        "projected_expense": round(projected_expense, 2) if projected_expense is not None else None,
        "projected_savings": round(projected_savings, 2) if projected_savings is not None else None,
        "days_remaining": remaining_days,
        "risks": risks,
        "signal_count": signal_count,
        "confidence": confidence,
        "headline": _headline(score, risks, projected_savings, has_financial_activity, signal_count),
    }


def _headline(score, risks, projected_savings, has_financial_activity=True, signal_count=0):
    if not has_financial_activity or score is None:
        return "Not enough data yet. Add income or expense transactions to unlock your Financial Health Score."
    if risks:
        return f"{len(risks)} budget risk{'s' if len(risks) != 1 else ''} detected before month-end."
    if projected_savings is not None and projected_savings < 0:
        return "Current pace points to a negative month-end cash-flow gap."
    if signal_count <= 1:
        return "Early score — add more financial history, budgets or goal progress to strengthen the signal."
    if score >= 75:
        return "Your recorded finances are showing strong momentum."
    return "Your finances are stable enough to improve with a few focused moves."


def simulate_purchase(context, amount, goals=None, subject=None, timeframe=None):
    """Explainable affordability simulation using only recorded Sigora data."""
    amount = max(_f(amount), 0)
    overall = context.get("overall") or {}
    history = context.get("monthly_savings_history") or []
    total_income = _f(overall.get("total_income"))
    total_expense = _f(overall.get("total_expense"))
    has_activity = bool(history) or total_income > 0 or total_expense > 0
    current_savings = _f(overall.get("savings"))
    recent = [_f(m.get("savings")) for m in history[-3:]]
    avg_monthly_savings = sum(recent) / len(recent) if recent else 0
    positive_pace = avg_monthly_savings if avg_monthly_savings > 0 else 0
    post_buffer = current_savings - amount
    buffer_used_pct = (amount / current_savings * 100) if current_savings > 0 else None
    recovery_months = (amount / positive_pace) if positive_pace > 0 else None

    goal_name = None
    if goals:
        incomplete = [g for g in goals if _f(g.get("current_amount")) < _f(g.get("target_amount"))]
        if incomplete:
            goal_name = incomplete[0].get("name")

    if not has_activity:
        level, ready = "insufficient", False
    elif amount <= 0:
        level, ready = "missing_amount", False
    elif current_savings <= 0 or post_buffer < 0:
        level, ready = "high", True
    elif buffer_used_pct is not None and buffer_used_pct >= 50:
        level, ready = "caution", True
    else:
        level, ready = "comfortable", True

    return {
        "amount": round(amount, 2), "subject": subject or "this decision", "timeframe": timeframe,
        "current_buffer": round(current_savings, 2), "post_buffer": round(post_buffer, 2),
        "buffer_used_pct": round(buffer_used_pct, 1) if buffer_used_pct is not None else None,
        "avg_monthly_savings": round(avg_monthly_savings, 2),
        "recovery_months": round(recovery_months, 1) if recovery_months is not None else None,
        "goal_name": goal_name, "level": level, "ready": ready,
    }
