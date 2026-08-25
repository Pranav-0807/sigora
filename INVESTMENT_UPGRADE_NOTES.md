# Sigora Invest Upgrade

Added a first-class investment intelligence module while intentionally excluding personalized security-level investment advice.

## Included now
- Investor risk/profile questionnaire (objective, horizon, volatility comfort, loss reaction, emergency-fund coverage, planned monthly contribution)
- Conservative / Moderate / Growth educational profile classification
- Educational model asset allocation examples
- Manual multi-asset portfolio tracker
- Quantity, average cost, current price, invested value, current value, gain/loss and return calculations
- Manual current-price updates (no fabricated live quotes)
- Asset-class and sector allocation breakdowns
- Concentration warnings for asset classes, sectors and single holdings
- Cash-flow readiness signals using Sigora's tracked income/expenses
- Emergency-liquidity precaution signals
- Research watchlist
- Educational investment explorer by asset class
- User-controlled compound-growth projection lab with explicit non-forecast warning
- AI portfolio insights integrating investor profile + portfolio + cash-flow context
- Strict AI prompt rules preventing named-security buy/sell/hold recommendations, target prices and return guarantees
- Invest navigation added to desktop + mobile UI
- PostgreSQL schema migration included in both runtime schema setup and schema.sql

## Intentionally excluded
- Personalized instructions to buy/sell a named stock/fund/security
- Exact user-specific allocation into named securities
- Guaranteed/target-return claims
- Fabricated live market data

Live prices/broker sync can be added later through a properly supported market-data or brokerage provider.

## Market research update
- Improved Invest-page text contrast/readability.
- Fixed Projection Lab Calculate Scenario JavaScript placement.
- Watchlist now accepts a company/fund/index name and resolves ticker + exchange automatically using public market search data.
- Watchlist cards show latest price and daily percentage change when available.
- Clicking a watchlist item opens a market research page with 5D/1M/6M/1Y/5Y charts, day/52-week ranges, and a plain-English explanation.
- Market data is informational and can be delayed/unavailable; no personalized buy/sell advice is produced.
