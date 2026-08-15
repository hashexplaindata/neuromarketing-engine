# STAGE 03 CONTRACT: N-FACTORIAL EXPERIMENT ENGINE

## Inputs
- Layer 4 (working): `../02_ensemble_saliency/output/detected_bboxes.json`
- Layer 4 (working): `../02_ensemble_saliency/output/raw_saliency_density.npy`
- Layer 3 (reference): `../../_config/math_guardrails.md`

## Process
1. If multi-variant input is detected, run:
   `python ../../scripts/n_factorial_compositor.py --bboxes detected_bboxes.json --out output/permutations/`
2. Execute benchmark evaluation via `pysaliency`:
   `python ../../scripts/pysaliency_evaluator.py --densities output/permutations/ --out output/`
3. Compute s-AUC (Shuffled AUC using off-target human fixation controls).
4. Compute NSS (Normalized Scanpath Saliency) against standardized fixation distributions.
5. Compute ANOVA main effects, interaction effects, and Cohen's d effect sizes between variants.
6. Enforce Guardrail C: Flag any variant with NSS < 1.5 as "Visually Scattered".

## Outputs
- `output/variant_leaderboard.json` -> Ranked variants by primary KPI with 95% Confidence Intervals
- `output/statistical_significance.json` -> ANOVA table, F-statistics, and Cohen's d values
