# Sigora currency integration

- Transactions keep their original amount and original currency.
- Dashboard, transactions, exports, reports, monthly savings, category totals and budget spending convert to the user's selected currency.
- Transaction conversion uses the transaction date and walks backward across non-business days.
- Budgets and goals store their currency. Changing the user's currency converts existing budgets/goals atomically using the current FX rate before saving the new preference. Future goal dates are never used as historical FX dates.
- Goal savings are converted from the user's current currency into the goal's stored currency when necessary.
- Existing installations are migrated automatically by `ensure_feature_schema()` before requests.
- FX rates use Frankfurter v2 and are cached per currency pair/date to reduce repeated network calls.
- Invalid/unsupported currency submissions are rejected and FX failures are shown as a settings error instead of a generic 500 page.
