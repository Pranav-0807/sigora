# Sigora Intelligence UX/Data Integrity Fix

This patch addresses two launch-blocking issues found during local testing:

1. **Intelligence discoverability**
   - Desktop sidebar navigation is now the scrollable middle pane while the brand and footer remain visible.
   - Intelligence is present in the mobile bottom navigation as **Health**.

2. **No fabricated Financial Health Score**
   - Brand-new accounts no longer receive neutral fallback scores.
   - Score components are included only when the supporting data exists.
   - No transaction history shows **Not enough data yet** instead of a numeric score.
   - Forecasts require current-month activity.
   - Stability requires at least two months of savings history.
   - What-if simulation refuses to present a meaningful verdict without financial history.

The health score is deterministic and explainable; missing signals are omitted rather than imputed.
