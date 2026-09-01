# SIGORA Balance Sheet Update — 2026-09-01

- Dashboard hierarchy: Total Cash, Investments, Liabilities, Net Worth.
- Net Worth = tracked cash + tracked investment value - tracked liabilities.
- Credit-card, loan and other-liability account balances are treated as liabilities.
- Bank/wallet/cash account balances are treated as cash assets.
- Account balance checkpoint model prevents statement closing balances from being double-counted.
- Manual transactions created after a balance checkpoint affect the displayed balance for asset and credit-card accounts.
- Loan principal is not guessed from generic expense transactions because EMI can include interest; users/provider update outstanding principal.
- SIGORA AI runtime limit messages and locked insight cards now use the selected app language.
