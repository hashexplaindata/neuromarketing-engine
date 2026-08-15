# CLAUDE ORCHESTRATION CONTRACT: HEROKU + APPWRITE + UPSTASH + CAMBER CLOUD

You are the single orchestrating agent for the Neuromarketing Production Engine.
Follow the Interpretable Context Methodology (ICM) across the specified cloud stack:

1. **Stack Execution Protocol**:
   - Web API hosted on Heroku (`api/main.py`).
   - Auth, database, and asset storage managed via Appwrite (`core/appwrite_service.py`).
   - Async job queue and progress streaming managed via Upstash Redis (`core/upstash_queue.py`).
   - Compute-heavy tensor operations executed via Camber Cloud GPU workers (`workers/camber_worker.py`).
2. **Zero Billing**: All authenticated requests proceed directly to GPU execution without Stripe or payment verification.
3. **Deterministic Scripts**: Delegate mechanical tasks to local scripts in `scripts/` passing `--input`, `--manifest`, and `--out`.
4. **Session Isolation**: Parameterize all stage operations with `tenant_id` and `session_id`.
