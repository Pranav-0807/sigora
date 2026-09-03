# SIGORA Money Model V2 — 2026-09-03

This build separates cash-flow history from current balances.

- Income and expenses can be linked to the user's actual account, wallet, credit card, Physical Cash, or left unassigned.
- Only accounts the user created appear dynamically; Physical Cash is always available and is initialized with a balance checkpoint on first use.
- Transfers create paired transfer movements and do not count as income or spending. Credit-card payments can therefore reduce the card liability without double-counting the original purchase.
- Cash & Bank is calculated only from tracked liquid-asset balance sources. If none are set up, SIGORA says so instead of inferring cash from transaction history; net worth is also withheld until a current liquid balance exists.
- Accounts now distinguish bank accounts, Physical Cash, stored-value digital wallets, and credit/debt. UPI apps that directly spend from a bank account should not be entered as separate wallets.
- Statement import requires an account when accounts exist, shows source account and review status, keeps duplicate protection, and conservatively treats obvious credit-card payments, ATM cash withdrawals, and explicit self-transfers as money movements rather than spending/income.
- Privacy notices explicitly state that manual accounts/imports do not give SIGORA bank-login access and that SIGORA never asks for bank passwords, PINs, CVVs or OTPs.
- New Money Model UX is localized in English, Tamil and Hindi.

Safety principle: if SIGORA cannot establish a financial fact from user-provided/imported data, it does not invent it.
