# SIGORA final repair — 2026-09-01

- Fixed translation dictionary startup KeyError for English phrase entries.
- Kept full Tamil/Hindi product-language pass, including tutorial and Premium/AI copy.
- Added landing/common account runtime translations.
- Added balance-sheet dashboard: Total Cash, Investments, Liabilities, Net Worth, monthly income/expenses.
- Account balances use checkpoint + later manual transactions; statement closing balances reset checkpoint.
- Credit cards/loans/other liabilities are separated from cash.
- Dashboard account/balance loading is fail-safe so an account migration/provider issue does not take the dashboard down.
- Financial-account balance schema is lazy-loaded instead of running on every page request.
- Existing bank account edit/delete, account-aware manual transactions, duplicate-account identity rules, statement normalization, Razorpay, Setu groundwork, market guards retained.
