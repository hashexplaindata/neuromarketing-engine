# STAGE 04 CONTRACT: DOMAIN BEHAVIORAL ROI ANALYTICS

## Inputs
- Layer 4 (working): `../02_ensemble_saliency/output/detected_bboxes.json`
- Layer 4 (working): `../02_ensemble_saliency/output/raw_saliency_density.npy`
- Layer 3 (reference): `../../_config/domain_boost_rules.md`

## Process
1. Identify active module from manifest (UI/UX, Image Ads, Shelf/Packaging, Content).
2. Calculate domain-specific ROI integrals:
   - UI/UX: CTA Visibility Index, Cognitive Load Score (CLS).
   - Ads: Brand Attention % = (integral_logo S(x,y) dx dy / integral_total S(x,y) dx dy) * 100.
   - Shelf: Shelf Standout Score (SSS) = mu(S_Target) / mu(S_Surrounding).
   - Content: Face-Text Gaze Alignment angle theta via cosine similarity.
3. Apply domain boost matrices (e.g., Face-gaze direction x1.3, CTA contour x1.25).

## Outputs
- `output/behavioral_scorecard.json` -> Domain metrics, percentile rankings, and ROI capture percentages
