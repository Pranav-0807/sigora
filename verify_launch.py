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
}
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
