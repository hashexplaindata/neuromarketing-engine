# STAGE 06 CONTRACT: STRATEGIC SYNTHESIS & REPORTING

## Inputs
- Layer 4 (working): `../01_asset_ingestion/output/low_level_metrics.json`
- Layer 4 (working): `../03_n_factorial_engine/output/variant_leaderboard.json`
- Layer 4 (working): `../04_domain_roi_analytics/output/behavioral_scorecard.json`
- Layer 4 (working): `../05_epistemic_validation/output/confidence_audit.json`
- Layer 3 (reference): `../../_config/report_design_system.md`

## Process
1. Act as Senior Behavioral Strategist (Claude 3.5 Sonnet prompt):
   - Ingest JSON metrics and write the Executive Scorecard (3 Key Strengths, 3 Critical Risks, Strategic Fixes).
2. Structure HTML document via format converter adhering to `report_design_system.md`.
3. Run local compilation script:
   `python ../../scripts/pdf_compiler.py --html output/executive_report.html --pdf output/executive_report.pdf`

## Outputs
- `output/executive_report.html` -> Standalone inspectable HTML report
- `output/executive_report.pdf` -> Final client-ready PDF deliverable
