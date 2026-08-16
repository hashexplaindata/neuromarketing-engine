# Neuromarketing Studio — Modal Migration Handoff

## What is required from the owner

Only two Modal service-user values are required by the Heroku API:

```text
MODAL_TOKEN_ID
MODAL_TOKEN_SECRET
```

Create them from the Modal workspace’s service-user/token settings. Do not use a personal token for production if a service-user token is available. Send these values only through a secure secret-management channel; never place them in chat, Git, the React client, or a committed file.

The Modal worker also needs one Modal Secret named `neuromarketing-studio-runtime`. It should contain the existing server-side Appwrite values and the Gemini configuration. This secret is created in Modal, not in the repository:

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

The user must also decide whether the Modal workspace is billed directly or through an eligible startup/student credit programme. Billing is a provider-account decision and must be verified in the Modal dashboard before production traffic is enabled.

## Deployment order

From a machine with the Modal CLI and the repository:

```bash
python3 -m pip install --user 'modal>=1.0.0,<2'
modal token new
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
modal deploy modal_app.py
```

The Heroku API then needs these server-side variables:

```text
GPU_PROVIDER=modal
MODAL_APP_NAME=neuromarketing-studio
MODAL_FUNCTION_NAME=process_job
MODAL_ENVIRONMENT=main
MODAL_TOKEN_ID=<service-user-token-id>
MODAL_TOKEN_SECRET=<service-user-token-secret>
```

The existing Appwrite and JWT values remain required. The frontend does not receive Modal credentials.

## Appwrite schema note

The current live `jobs` collection does not yet contain `provider` or `provider_job_id` columns. The code therefore keeps those fields disabled by default through `APPWRITE_PROVIDER_FIELDS_ENABLED=false`, while still submitting Modal jobs and preserving the canonical Appwrite job/result lifecycle. After the columns are deliberately provisioned and tested, set:

```text
APPWRITE_PROVIDER_FIELDS_ENABLED=true
```

Do not enable this flag before the columns exist.

## What was removed from the repository

The migration removes the public Camber App/Job runbook, App definition, Camber worker daemon, Upstash queue module, Redis Pub/Sub WebSocket, Celery task path, Upstash diagnostic, and Camber-era tests. The worker is now `workers/modal_worker.py`; the deployment module is `modal_app.py`; and the bounded local script is `scripts/modal_headless_smoke.py`.

## Safe Camber cleanup in WSL

The malformed Camber App was already deleted. The private Stash smoke bundle was also deleted after the test. Failed historical Jobs 23982, 23983, and the successful-start Job 23984 are cloud-side records; do not confuse them with local files. If the Camber console does not expose a job-delete operation, ask Camber support about retention/purge rather than guessing a destructive command.

To inspect the local CLI before removal:

```bash
command -v camber || true
camber version || true
python3 -m pip show camber cambercloud 2>/dev/null || true
```

If the CLI was installed with pip and the package listing confirms the package name, remove only that confirmed package:

```bash
python3 -m pip uninstall <confirmed-camber-package-name>
```

If it is a standalone binary, record its path first and remove only that exact file:

```bash
CAMBER_BIN="$(command -v camber)"
printf 'Camber binary: %s\n' "$CAMBER_BIN"
readlink -f "$CAMBER_BIN"
```

Search for local Camber configuration without printing secret contents:

```bash
find "$HOME/.config" "$HOME/.cache" "$HOME/.local/share" "$HOME" \
  -maxdepth 4 \
  \( -iname '*camber*' -o -iname '*cambercloud*' \) \
  -print 2>/dev/null
```

Review the paths manually. Delete only confirmed Camber-specific credential/configuration directories, for example:

```bash
rm -rf -- "$HOME/<confirmed-camber-config-directory>"
```

Do not run a broad command such as `rm -rf ~/.config` or delete the entire WSL distribution. The repository itself is not a Camber credential store; retain it for the Modal migration after pulling `main`.

Finally, remove Camber environment variables from shell startup files only after inspecting the matching lines:

```bash
grep -nE 'CAMBER|camber' ~/.bashrc ~/.profile ~/.zshrc 2>/dev/null || true
```

Delete only the matching Camber export lines, then restart the shell. Never paste the values of any remaining secrets.
