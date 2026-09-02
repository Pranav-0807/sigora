# SIGORA launch polish — 2026-09-02

Scope is deliberately limited to polishing the tested Investments V2 upgrade and the untranslated dashboard surfaces visible during local QA. Existing product areas are retained.

## Fixed
- Ticker resolver runtime dependency (`import math`) included in the package.
- Compact holding rows and overflow detail popover now force readable dark foregrounds on light cards.
- Positive/negative values retain semantic contrast.
- Investments V2 user-facing copy is localized for English, Tamil and Hindi across onboarding, holdings, warnings, Scenario Lab, educational sections and watchlist.
- Portfolio warning sentences are localized server-side, including dynamic concentration percentages and holding names.
- Investment Explorer descriptions/risk/horizon labels receive Tamil/Hindi phrase coverage.
- Dashboard Financial Intelligence sublabels, momentum labels and the dashboard SIGORA insight card are localized for English, Tamil and Hindi.

## Safety / product behavior retained
- Bought/average price remains recorded cost basis.
- Current supported market price is resolved/refreshed separately and may be delayed.
- No personalized buy/sell advice or guaranteed returns.
- No unrelated feature rebuilds in this polish pass.
