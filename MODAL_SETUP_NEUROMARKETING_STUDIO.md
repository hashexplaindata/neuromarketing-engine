# Modal Setup for Neuromarketing Studio

## Purpose

Neuromarketing Studio uses Modal for private GPU execution. Heroku remains the authenticated API gateway, Appwrite remains the tenant-scoped durable database and artifact store, and the React client continues polling the authenticated job endpoint. Modal call IDs are execution references; they are not the business source of truth.

```text
React Studio → Heroku API → Appwrite job + asset → Modal async L4 Function
                                                   ↓
                              Appwrite result envelope + artifacts
                                                   ↓
                              React durable status polling
```

## Credentials required

Two credentials are required for the Heroku API to submit Modal calls:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
```

Create these as a Modal service-user token, not a personal developer token, for production. The Modal SDK reads these environment variables directly. Never commit them, place them in the React client, or paste them into chat.

The Modal worker also needs a server-side secret named `neuromarketing-studio-runtime`. It should contain the existing Appwrite service credentials and optional Gemini configuration:

```text
APPWRITE_ENDPOINT
APPWRITE_PROJECT_ID
APPWRITE_API_KEY
APPWRITE_DATABASE_ID
APPWRITE_JOBS_COLLECTION_ID
APPWRITE_RESULTS_COLLECTION_ID
APPWRITE_STORAGE_BUCKET_ID
GEMINI_API_KEY
GEMINI_MODEL
```

The Gemini key is optional for deterministic pipeline execution, but the worker must keep the fallback explicitly labelled while Gemini quota is exhausted.

## Local installation and authentication

On the deployment machine, install the Modal CLI and authenticate the account that owns the production workspace:

```bash
python3 -m pip install --user 'modal>=1.0.0,<2'
modal token new
```

For CI or a production deploy machine, use the Modal service-user token through environment variables rather than interactive login:

```bash
export MODAL_TOKEN_ID='do-not-paste-this-value-in-chat'
export MODAL_TOKEN_SECRET='do-not-paste-this-value-in-chat'
```

## Create the worker secret

Create the secret in the Modal workspace once. Use the real values locally; do not commit the command with values into Git:

```bash
modal secret create neuromarketing-studio-runtime \
  APPWRITE_ENDPOINT="$APPWRITE_ENDPOINT" \
  APPWRITE_PROJECT_ID="$APPWRITE_PROJECT_ID" \
  APPWRITE_API_KEY="$APPWRITE_API_KEY" \
  APPWRITE_DATABASE_ID="$APPWRITE_DATABASE_ID" \
  APPWRITE_JOBS_COLLECTION_ID="$APPWRITE_JOBS_COLLECTION_ID" \
  APPWRITE_RESULTS_COLLECTION_ID="$APPWRITE_RESULTS_COLLECTION_ID" \
  APPWRITE_STORAGE_BUCKET_ID="$APPWRITE_STORAGE_BUCKET_ID" \
  GEMINI_API_KEY="$GEMINI_API_KEY" \
  GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
```

## Deploy the Modal function

Run from the repository root:

```bash
modal deploy modal_app.py
```

The deployed function is named `process_job` in the Modal application `neuromarketing-studio`. The deployment builds the existing `Dockerfile.worker`, which contains the full CUDA/PyTorch/DeepGaze/YOLO/EasyOCR runtime. Modal requests one NVIDIA L4 GPU per function container, a 30-minute timeout, and two retries for transient failures.

## Configure Heroku

The API dyno needs the Modal SDK and service-user credentials. Configure the following values in Heroku’s server-side environment only:

```bash
heroku config:set \
  GPU_PROVIDER=modal \
  MODAL_APP_NAME=neuromarketing-studio \
  MODAL_FUNCTION_NAME=process_job \
  MODAL_ENVIRONMENT=main \
  MODAL_TOKEN_ID='service-user-id' \
  MODAL_TOKEN_SECRET='service-user-secret' \
  --app neuromarketing-suite-eb8efca8edd1
```

The existing Appwrite and JWT secrets must remain configured. Do not set Modal credentials in Vite or any `VITE_*` frontend variable.

## Smoke test

The first smoke test must use a repository-owned image and a non-sensitive tenant. Submit through the deployed Modal function using the SDK, store the returned call ID only in a local file, and verify that the Appwrite job becomes `RUNNING` and then `COMPLETE`. Confirm that the result envelope contains the expected schema and that heatmap/focus/scanpath artifacts are persisted in Appwrite.

A smoke test is not a production readiness proof. Before enabling customer traffic, test timeout handling, Modal retries, duplicate callback/idempotency behavior, Appwrite artifact reconciliation, browser refresh recovery, and tenant isolation.

## Provider-neutral lifecycle

The Heroku API creates the durable Appwrite job before submission. It submits the canonical task payload to Modal and stores `provider="modal"` plus the Modal call ID in the job record. The Modal worker updates Appwrite at `RUNNING`, `COMPLETE`, or `FAILED`, saves the result envelope, and uploads visual artifacts. The React client polls Appwrite through Heroku; no Redis Pub/Sub or WebSocket dependency is required for correctness.

## Camber status

Camber is no longer part of the production architecture. Do not create Camber Apps or Jobs, upload Stash bundles, or keep Camber credentials in deployment environments. The old Camber runbook and App template have been removed from the repository. Local WSL cleanup commands are documented separately in the migration handoff.
