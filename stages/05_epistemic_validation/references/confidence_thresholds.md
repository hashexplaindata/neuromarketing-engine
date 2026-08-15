# EPISTEMIC VALIDATION & CONFIDENCE THRESHOLDS

## Model Agreement Decision Matrix
| Linear Correlation (CC) | KL Divergence (KLD) | Confidence Tier | Confidence Score | Automation Action |
| :--- | :--- | :--- | :--- | :--- |
| `CC > 0.80` | `KLD < 0.35` | **High Confidence** | 85% – 100% | Direct Automated Delivery |
| `0.65 <= CC <= 0.80` | `0.35 <= KLD <= 0.60` | **Moderate Confidence**| 70% – 84% | Warning Flag in Executive Summary |
| `CC < 0.65` | `KLD > 0.60` | **Low Confidence** | < 70% | Epistemic Disclaimer & Human Panel Recommendation |

## Standard Epistemic Disclaimer Clause
> *"High Uncertainty Flag: Significant divergence detected between bottom-up visual saliency engines (DeepGaze III vs. UMSI). Recommend secondary empirical validation with live human eye-tracking cohort."*
