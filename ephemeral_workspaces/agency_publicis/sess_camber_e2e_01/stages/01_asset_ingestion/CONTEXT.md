# STAGE 01 CONTRACT: ASSET INGESTION & EARLY CORTEX

## Inputs
- Layer 4 (working): `input_assets/` (Raw image/Figma frame export)
- Layer 3 (reference): `references/aspect_ratios.md`
- Layer 3 (reference): `../../_config/billing_tiers.md`

## Process
1. Verify user Stripe token and rate limits against `billing_tiers.md`.
2. Run local script: `python ../../scripts/opencv_preprocessor.py --input input_assets/ --output output/`
3. Execute low-level image stress analysis:
   - Calculate visual entropy: H = -sum(p * log2(p))
   - Extract Canny edge density and Michelson contrast ratio.
   - Resize and normalize assets to standard model tensors.

## Outputs
- `output/manifest.json` -> Standardized tensor paths and metadata
- `output/low_level_metrics.json` -> Visual entropy, edge density, and contrast scores
