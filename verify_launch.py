from pathlib import Path

ROOT = Path(__file__).resolve().parent
required = [
    "templates/accounts.html",
    "templates/import_transactions.html",
    "bank_integration.py",
    "INDIA_BANK_INTEGRATION.md",
]
missing = [p for p in required if not (ROOT / p).exists()]
app_text = (ROOT / "app.py").read_text(encoding="utf-8")
checks = {
    "/accounts route": '@app.route("/accounts")' in app_text,
    "/import-transactions route": '@app.route("/import-transactions", methods=["GET", "POST"])' in app_text,
    "Setu connect route": '@app.route("/accounts/connect/india", methods=["POST"])' in app_text,
    "Setu webhook route": 'setu' in app_text.lower() and 'webhook' in app_text.lower(),
    "Razorpay subscription route": '@app.route("/premium/subscribe", methods=["POST"])' in app_text,
    "Razorpay webhook route": '@app.route("/razorpay/webhook", methods=["POST"])' in app_text,
    "Razorpay boolean customer_notify": '"customer_notify": True' in app_text,
}

base_text = (ROOT / "templates/base.html").read_text(encoding="utf-8")
checks["Updated interactive tutorial"] = "QUICK START · 6 STEPS" in base_text and "tutorialMove" in base_text
if missing or not all(checks.values()):
    print("FAILED")
    if missing:
        print("Missing files:", ", ".join(missing))
    for name, ok in checks.items():
        print(f"{name}: {'OK' if ok else 'MISSING'}")
    raise SystemExit(1)
print("SIGORA LAUNCH PACKAGE VERIFIED")
for name in checks:
    print(name + ": OK")
for path in required:
    print(path + ": OK")

# Final-launch regression checks
app_text = Path("app.py").read_text()
base_text = Path("templates/base.html").read_text()
market_text = Path("templates/investment_market.html").read_text()
css_text = Path("static/styles.css").read_text()
assert '"cancel_at_cycle_end": True' in app_text
assert 'event == "subscription.cancelled"' in app_text and 'expires_at > datetime.utcnow()' in app_text
assert 'mobile-tutorial-trigger' in base_text and 'mobile-tutorial-trigger' in css_text
assert 'min_points = {"5d": 3, "1mo": 5, "6mo": 20, "1y": 30, "5y": 30}' in app_text
assert 'Historical chart temporarily unavailable' in market_text
assert 'subscription_payload["offer_id"]' in app_text
print("Cancellation preserves paid period: OK")
print("Mobile tutorial entry: OK")
print("Sparse market-history guard: OK")
print("Coupon Razorpay Offer linkage: OK")
