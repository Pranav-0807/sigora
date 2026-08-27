# Sigora Intelligence Upgrade

## Added
- Explainable Financial Health Score (0–100)
- Month-end expense and savings projection
- Predictive budget-breach detection
- Daily correction amount for at-risk budgets
- Premium What-if purchase simulator
- Dynamic Premium feature messaging based on current signals
- Fixed regional Premium pricing by user currency
- Currency-specific Razorpay plan selection; checkout fails closed if a matching plan is not configured

## Razorpay deployment
Keep `RAZORPAY_PLAN_ID` for INR. For every international currency you actually sell, create a matching Razorpay subscription plan and set `RAZORPAY_PLAN_ID_USD`, `RAZORPAY_PLAN_ID_EUR`, etc. Do not point two currencies at the same plan unless Razorpay confirms the plan currency matches.

## Product principle
The deterministic engine calculates forecasts/scores from recorded data. Gemini explains data but is not trusted to invent calculations. This makes the competition story stronger and the product safer.

## Important
Forecasts are estimates, not guarantees or regulated financial advice. Regional prices are product prices, not live FX conversions.
