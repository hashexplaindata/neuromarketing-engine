# STAGE 05 CONTRACT: EPISTEMIC VALIDATION

## Inputs
- Layer 4 (working): `../02_ensemble_saliency/output/raw_saliency_density.npy`
- Layer 4 (working): `../04_domain_roi_analytics/output/behavioral_scorecard.json`
- Layer 3 (reference): `../../_config/math_guardrails.md`

## Process
1. Compute ensemble agreement between DeepGaze III and UMSI:
   - Calculate Linear Correlation Coefficient (CC) and Kullback-Leibler Divergence (KLD) between models.
2. Score confidence:
   - CC > 0.80 & KLD < 0.35 -> High Confidence (Score: 85-100%).
   - CC 0.65-0.80 -> Medium Confidence (Score: 70-84%).
   - CC < 0.65 -> Low Confidence (<70%).
3. Generate Epistemic Disclaimer if confidence < 70%:
   "High Uncertainty Flag: Divergence between bottom-up saliency engines. Validate with live human panel."

## Outputs
- `output/confidence_audit.json` -> Model agreement metrics, CC/KLD matrices, and uncertainty flags
