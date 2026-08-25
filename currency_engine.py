import os
from datetime import datetime, timedelta, date as date_type
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

import requests

# Frankfurter v2 provides current and historical FX rates from multiple
# official providers. The base URL can be overridden for testing/self-hosting.
FX_API = os.getenv("SIGORA_FX_API", "https://api.frankfurter.dev/v2").rstrip("/")


def _round_money(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _normalise_currency(value):
    return str(value or "INR").strip().upper()


def _normalise_date(value):
    if hasattr(value, "strftime"):
        value = value.strftime("%Y-%m-%d")
    current = datetime.strptime(str(value), "%Y-%m-%d").date()
    # Future dates do not have an FX rate yet. For goals/budgets we want the
    # current rate when re-denominating a value, so clamp future dates to today.
    today = date_type.today()
    return min(current, today)


@lru_cache(maxsize=4096)
def _fetch_rate(from_currency, to_currency, requested_date):
    """Fetch and cache one FX rate for a currency pair/date."""
    url = f"{FX_API}/rate/{from_currency}/{to_currency}"
    try:
        response = requests.get(
            url,
            params={"date": requested_date},
            timeout=10,
        )
        if response.ok:
            payload = response.json()
            rate = payload.get("rate")
            if rate is not None:
                return float(rate)
    except (requests.RequestException, ValueError, TypeError):
        pass
    return None


def get_historical_rate(from_currency, to_currency, conversion_date):
    from_currency = _normalise_currency(from_currency)
    to_currency = _normalise_currency(to_currency)

    if from_currency == to_currency:
        return 1.0

    current = _normalise_date(conversion_date)

    # FX providers may not publish a rate on weekends/holidays. Walk back up
    # to seven days to find the latest available rate for that date.
    for _ in range(7):
        rate = _fetch_rate(
            from_currency,
            to_currency,
            current.strftime("%Y-%m-%d"),
        )
        if rate is not None:
            return rate
        current -= timedelta(days=1)

    raise RuntimeError(
        f"Unable to obtain an FX rate for {from_currency}->{to_currency} "
        f"around {conversion_date}. Please try again shortly."
    )


def convert_amount(amount, from_currency, to_currency, conversion_date):
    rate = get_historical_rate(from_currency, to_currency, conversion_date)
    return _round_money(Decimal(str(amount)) * Decimal(str(rate)))


def convert_transaction(transaction, target_currency):
    result = dict(transaction)
    original_currency = _normalise_currency(transaction.get("currency"))
    target_currency = _normalise_currency(target_currency)
    result["original_amount"] = float(transaction["amount"])
    result["original_currency"] = original_currency
    result["display_currency"] = target_currency
    result["amount"] = convert_amount(
        transaction["amount"],
        original_currency,
        target_currency,
        transaction["date"],
    )
    return result
