# Interpretable Context Methodology (ICM) Neuromarketing Engine

This repository implements a deterministic filesystem-based agent architecture for neuromarketing attention prediction, statistical A/B/n testing, and executive report synthesis.

## Architecture: 5-Layer Context Hierarchy
1. **Layer 0 (`CLAUDE.md`)**: Structural identity & execution constraints.
2. **Layer 1 (`CONTEXT.md`)**: Pipeline routing & stage sequence.
3. **Layer 2 (`stages/0X_*/CONTEXT.md`)**: Stage-specific contracts (Inputs, Process, Outputs).
4. **Layer 3 (`_config/`, `references/`)**: Invariant rules, formulas, and domain parameters.
5. **Layer 4 (`stages/0X_*/output/`)**: Inspectable intermediate JSON/NPY/HTML artifacts.

## Quickstart
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Place target images/creative assets in `input_assets/`.
3. Execute stages sequentially or instruct an AI orchestrator to step through `stages/01_asset_ingestion` to `stages/06_strategic_synthesis`.
