# WORKSPACE PIPELINE & CLOUD ROUTING

## Pipeline Stages
- Stage 01: Asset Ingestion & Early Visual Cortex (`stages/01_asset_ingestion/`)
- Stage 02: Ensemble Saliency & Component Detection (`stages/02_ensemble_saliency/`)
- Stage 03: N-Factorial Combinatorics & Evaluation (`stages/03_n_factorial_engine/`)
- Stage 04: Domain Behavioral ROI Analytics (`stages/04_domain_roi_analytics/`)
- Stage 05: Epistemic Validation & Confidence Scoring (`stages/05_epistemic_validation/`)
- Stage 06: Strategic Synthesis & Figma Delivery (`stages/06_strategic_synthesis/`)

## Cloud Infrastructure
- **Heroku**: FastAPI Router & WebSocket Server (`Procfile`)
- **Appwrite**: Authentication, Document Database, Asset Storage (`core/appwrite_service.py`)
- **Upstash Redis**: Serverless Queue & Pub/Sub (`core/upstash_queue.py`)
- **Camber Cloud**: GPU Execution Cluster (`workers/camber_worker.py`)
- **Billing Layer**: NONE (Zero monetization constraints)
