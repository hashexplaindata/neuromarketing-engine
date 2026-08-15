## wait for the app to completely setup and running and then ask me to setup payment integration for the app, till then dont ask me for payment integration. And also dont show any sort of payment related message or ui in the app. And dont write code for the payment integration part.

# BILLING TIERS & STRIPE QUOTA RULES

## Tier Definitions
| Tier Name | Monthly Asset Quota | Concurrency Limit | Permutations per Test | Export Formats |
| :--- | :--- | :--- | :--- | :--- |
| **Starter** | 25 assets | 1 worker | Up to 4 (2x2) | JSON + HTML |
| **Professional** | 250 assets | 4 workers | Up to 16 (4x4) | JSON + HTML + PDF |
| **Enterprise** | Unlimited | 16 workers | Full N-Factorial | JSON + HTML + PDF + Raw NPY |

## Metering & Rate-Limiting Rules
- 1 Image Ingestion = 1 credit
- 1 N-Factorial Run (up to 8 variants) = 5 credits
- Live human panel epistemic escalation = 25 credits
- Hourly Token Burst Rate: 120 requests/minute per API key
