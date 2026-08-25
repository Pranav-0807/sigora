"""India Account Aggregator integration for Sigora.

Uses Setu's AA Gateway. Production access requires Setu/Sahamati onboarding and
credentials; sandbox can be used for end-to-end testing before go-live.
"""
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import requests

SETU_BASE_URL = os.getenv("SETU_AA_BASE_URL", "https://fiu.setu.co").rstrip("/")
SETU_AUTH_URL = os.getenv("SETU_AA_AUTH_URL", "https://accountservice.setu.co/v1/users/login").rstrip("/")
SETU_CLIENT_ID = os.getenv("SETU_AA_CLIENT_ID", "").strip()
SETU_CLIENT_SECRET = os.getenv("SETU_AA_CLIENT_SECRET", "").strip()
SETU_PRODUCT_INSTANCE_ID = os.getenv("SETU_AA_PRODUCT_INSTANCE_ID", "").strip()
SETU_REDIRECT_URL = os.getenv("SETU_AA_REDIRECT_URL", "").strip()
SETU_PURPOSE_CODE = os.getenv("SETU_AA_PURPOSE_CODE", "101").strip()
SETU_PURPOSE_TEXT = os.getenv("SETU_AA_PURPOSE_TEXT", "Personal financial management").strip()
SETU_DATA_LIFE_VALUE = int(os.getenv("SETU_AA_DATA_LIFE_VALUE", "1"))
SETU_DATA_LIFE_UNIT = os.getenv("SETU_AA_DATA_LIFE_UNIT", "MONTH").strip().upper()
SETU_FETCH_TYPE = os.getenv("SETU_AA_FETCH_TYPE", "PERIODIC").strip().upper()
SETU_FREQUENCY_VALUE = int(os.getenv("SETU_AA_FREQUENCY_VALUE", "1"))
SETU_FREQUENCY_UNIT = os.getenv("SETU_AA_FREQUENCY_UNIT", "MONTH").strip().upper()

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


def configured() -> bool:
    return bool(SETU_CLIENT_ID and SETU_CLIENT_SECRET and SETU_PRODUCT_INSTANCE_ID)


def _token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["token"]
    if not SETU_CLIENT_ID or not SETU_CLIENT_SECRET:
        raise RuntimeError("Indian bank connection is not configured yet. Add Setu Account Aggregator credentials in the deployment environment.")
    response = requests.post(
        SETU_AUTH_URL,
        headers={"client": "bridge", "Content-Type": "application/json"},
        json={"clientID": SETU_CLIENT_ID, "secret": SETU_CLIENT_SECRET, "grant_type": "client_credentials"},
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    token = data.get("access_token") or data.get("data", {}).get("token")
    if not token:
        raise RuntimeError("Setu authentication succeeded but no access token was returned.")
    _token_cache["token"] = token
    _token_cache["expires_at"] = now + int(data.get("expires_in", data.get("data", {}).get("expiresIn", 300)))
    return token


def _request(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update({"Authorization": f"Bearer {_token()}", "Content-Type": "application/json", "x-product-instance-id": SETU_PRODUCT_INSTANCE_ID})
    response = requests.request(method, f"{SETU_BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
    if response.status_code == 401:
        _token_cache["token"] = None
        headers["Authorization"] = f"Bearer {_token()}"
        response = requests.request(method, f"{SETU_BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
    response.raise_for_status()
    return response.json()


def create_consent(mobile: str, redirect_url: Optional[str] = None, days: int = 120) -> dict:
    """Create a Setu AA consent request using the current AA Gateway API.

    Consent object details (FI type, purpose, fetch type, frequency, data life)
    are configured on Setu Bridge for the product instance.
    """
    mobile = "".join(ch for ch in mobile if ch.isdigit())
    if mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]
    if len(mobile) != 10:
        raise ValueError("Enter a valid 10-digit Indian mobile number.")
    now = datetime.now(timezone.utc)
    data_from = now - timedelta(days=365 * 2)
    body = {
        "consentDuration": {"unit": "DAY", "value": str(max(1, days))},
        "vua": mobile,
        "dataRange": {
            "from": data_from.isoformat().replace("+00:00", "Z"),
            "to": now.isoformat().replace("+00:00", "Z"),
        },
        "context": [],
        "additionalParams": {"tags": ["Sigora_PFM"]},
    }
    # Setu returns the consent webview URL in the response. redirect_url is kept
    # for backward compatibility with Sigora callers; Bridge controls callback UI.
    return _request("POST", "/consents", json=body)

def get_consent(consent_id: str) -> dict:
    return _request("GET", f"/consents/{consent_id}")


def create_session(consent_id: str, start: str, end: str) -> dict:
    return _request("POST", "/sessions", json={"consentId": consent_id, "dataRange": {"from": start, "to": end}, "format": "json"})


def get_session(session_id: str) -> dict:
    return _request("GET", f"/sessions/{session_id}")


def parse_transactions(payload: dict) -> list[dict]:
    """Normalize Setu FI data into Sigora transaction records."""
    result = []
    roots = []
    for fi in payload.get("fiData", []) or []:
        for item in fi.get("data", []) or []:
            roots.append(item.get("decryptedFI") or item.get("data") or {})
    if not roots and payload.get("fips"):
        for fip in payload.get("fips", []):
            for account in fip.get("accounts", []):
                data = account.get("data") or {}
                roots.append(data.get("account", data))
    for account in roots:
        acc = account.get("account", account)
        masked = acc.get("maskedAccNumber") or ""
        currency = (acc.get("currency") or "INR").upper()
        txns = (acc.get("transactions") or {}).get("transaction", [])
        for txn in txns:
            raw_type = str(txn.get("type", "DEBIT")).upper()
            transaction_type = "income" if raw_type in {"CREDIT", "CREDITS"} else "expense"
            try:
                amount = abs(float(txn.get("amount", 0)))
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue
            timestamp = txn.get("valueDate") or txn.get("transactionTimestamp") or txn.get("date")
            if not timestamp:
                continue
            date = str(timestamp)[:10]
            description = str(txn.get("narration") or txn.get("description") or txn.get("reference") or "Bank transaction").strip()
            result.append({
                "transaction_type": transaction_type,
                "amount": amount,
                "currency": currency,
                "category": "",
                "description": description,
                "date": date,
                "source": "setu_aa",
                "external_id": str(txn.get("txnId") or txn.get("reference") or f"{date}:{amount}:{description}"),
                "account_masked": masked,
                "mode": txn.get("mode"),
            })
    return result

def parse_accounts(payload: dict) -> list[dict]:
    accounts=[]
    for fi in payload.get("fiData", []) or []:
        fip_id=fi.get("fipID") or "Indian bank"
        for item in fi.get("data", []) or []:
            account=(item.get("decryptedFI") or item.get("data") or {}).get("account", {})
            if account:
                accounts.append({"institution_name": fip_id, "account": account, "currency": (account.get("currency") or "INR").upper()})
    if not accounts:
        for fip in payload.get("fips", []) or []:
            fip_id=fip.get("fipID") or "Indian bank"
            for item in fip.get("accounts", []) or []:
                account=(item.get("data") or {}).get("account", item.get("data") or {})
                if account:
                    accounts.append({"institution_name": fip_id, "account": account, "currency": (account.get("currency") or "INR").upper()})
    return accounts
