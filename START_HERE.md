# Sigora — Final India Bank Build

This package includes both visible pages:
- `/import-transactions` — statement import
- `/accounts` — Indian bank accounts / Setu Account Aggregator

## Local start on macOS
From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Then sign in. On desktop, **Import** and **Bank accounts** appear in the left sidebar. On compact/mobile layouts, both also appear in the bottom navigation.

Real bank connectivity requires Setu AA sandbox/production credentials. Without those credentials the Bank Accounts page still opens and clearly shows that connectivity is not activated yet.
