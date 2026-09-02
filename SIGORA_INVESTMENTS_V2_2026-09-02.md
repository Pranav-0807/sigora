# SIGORA Investments V2 — 2026-09-02

This is an additive Investments upgrade. Existing SIGORA product areas remain unchanged.

## Added
- Automatic refresh of supported holding market prices using the existing market-data engine, with a 15-minute freshness window and bounded concurrent refreshes so large portfolios do not block the page indefinitely.
- Bought/average cost remains the recorded cost basis; market price updates never overwrite it.
- Compact Top-5 holdings experience with search, sort, progressive View All, and compact mobile rows.
- Portfolio Intelligence summary: current value, invested cost, gain/loss and estimated today's move.
- Explainable educational Portfolio Health signals.
- Goal Connection comparing current tracked portfolio value with recorded goal targets without treating market value as guaranteed goal funding.
- Portfolio → Life context: investment share of net worth, largest holding, emergency-cover context and deterministic 20% downside impact.
- Collapsed Scenario Lab for contribution/return illustrations and portfolio/net-worth shocks.
- English, Tamil and Hindi strings for all new Investments V2 surfaces.
- Existing watchlist, market research, investor profile, allocation education and SIGORA AI remain available.

## Guardrails
- No buy/sell recommendations.
- No invented prices.
- No guaranteed returns.
- Market prices can be delayed or temporarily unavailable.
- International market prices are converted into the holding's stored/base currency before portfolio aggregation when FX conversion is available.
