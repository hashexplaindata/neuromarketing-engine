# Neuromarketing Studio — Private Camber Job Setup

This runbook deploys the Neuromarketing Studio GPU worker as a **private, headless Camber Job**. It does not create a Camber Science App. Science Apps are directory-facing interactive workloads; the Neuromarketing Studio worker is an internal asynchronous B2B processor that consumes a queue task, runs visual diagnostics, and persists tenant-scoped results.

## Production architecture

```text
Neuromarketing Studio React client
        |
        v
Heroku authenticated API gateway
        |
        v
Upstash Redis queue + Appwrite job record
        |
        v
Private Camber Job on an L4 GPU
        |
        v
Appwrite result envelope + tenant-scoped artifacts
```

The Heroku dyno remains lightweight. It receives authenticated requests, stores the input asset, records the canonical job, and enqueues work. The private Camber Job performs GPU inference. The Camber worker must never receive client credentials through a committed file, container layer, or public App definition.

## Verified Camber Job contract

The installed Camber CLI reports the following job command contract:

```bash
camber job create \
  --cmd '<command>' \
  --engine <base|mpi|mesa|athena|nextflow|gromacs|lammps|openfoam> \
  --gpu \
  --num-nodes 1 \
  --path stash://<username>/<project>/ \
  --size <xxsmall|xsmall|small|medium|large>
```

The `base` engine is the first candidate for a Python worker because Camber describes it as including PyTorch, pandas, matplotlib, MPI, and related scientific packages. The `mpi` engine is not assumed to contain the Neuromarketing Studio runtime merely because it is available. The selected engine must be validated by the smoke job.

The command contract exposes no image argument. Therefore, the initial headless Job path must use a private Stash bundle and Camber’s available execution environment. The GHCR worker image remains a reproducible build artifact, but it is not assumed to be consumable by `camber job create` until Camber documents an image/runtime option for Jobs.

## Secret-free Stash bundle

The bundle must contain the minimum source required for the bounded smoke script and must exclude `.env`, API keys, model caches, generated output, frontend files, tests, and client assets. From the repository root in the authenticated WSL terminal, first verify the recursive-copy flags:

```bash
camber stash cp --help
```

Then upload a prepared bundle using the private Stash path returned by `camber login`:

```bash
camber stash cp -r \
  --use-gitignore \
  --exclude '.env' \
  --exclude 'studio' \
  --exclude 'tests' \
  --exclude 'output' \
  --exclude 'models' \
  --exclude 'ephemeral_workspaces' \
  . \
  stash://<username>/neuromarketing-studio-smoke/
```

The bundle still needs a runtime configuration strategy for production Upstash and Appwrite access. Do not upload those secrets. For the first smoke, the script uses the local Appwrite fallback and a repository-owned image, so it does not require client credentials or a live queue.

## Bounded smoke command

The canonical worker daemon is a long-running queue consumer. Do not use `python -m workers.camber_worker` as the first smoke command because it is designed to wait for queue tasks. The repository includes a bounded script at `scripts/camber_headless_smoke.py`. It processes one repository-owned test JPEG through the real pipeline, uses the local Appwrite fallback, writes a result envelope to `/tmp/camber_smoke_result.json`, prints `NEUROMARKETING_STUDIO_CAMBER_SMOKE_OK`, and exits.

Before launching compute, verify the private bundle contains the smoke script and test asset:

```bash
camber stash ls stash://<username>/neuromarketing-studio-smoke/
camber stash test stash://<username>/neuromarketing-studio-smoke/scripts/camber_headless_smoke.py
camber stash test stash://<username>/neuromarketing-studio-smoke/input_assets/user_test_thumbnail.jpg
```

The first execution should use the smallest confirmed GPU-capable size. The account’s observed resource examples identify `XSMALL` as the smallest L4 profile, while the CLI accepts the lowercase value `xsmall` for `--size`. Start with one node and `--gpu`; use `medium` only if the smoke logs demonstrate a memory requirement and the additional cost is approved.

A first candidate command is:

```bash
camber job create \
  --engine base \
  --size xsmall \
  --gpu \
  --num-nodes 1 \
  --path stash://<username>/neuromarketing-studio-smoke/ \
  --cmd "cd /workspace/neuromarketing-studio-smoke && python3 scripts/camber_headless_smoke.py" \
  --output json
```

The exact Stash mount path inside the Camber runtime is not established by the CLI help. If `/workspace/neuromarketing-studio-smoke` is not the runtime path, the command must be adjusted using the path shown in the job logs; do not guess repeatedly or create duplicate GPU jobs.

## Job lifecycle evidence

The CLI help does not show whether `camber job get` and `camber job logs` take a positional job ID or resolve a selected job. After one approved submission, use the exact accepted syntax from the CLI and capture only non-secret evidence:

```bash
camber job list --output json --page 1 --size 10
camber job get --output json
camber job logs
```

Record the job ID, status sequence, engine, size, GPU flag, timestamps, smoke marker, output path, and failure text if present. Do not paste API keys, environment variables, or private Stash URLs containing sensitive tokens.

## Production integration gate

A successful bounded smoke proves that the chosen Camber engine can start the worker bundle, access the test asset, load the required models, and produce a result envelope. It does not yet prove production dispatch. The provider adapter must later persist the Camber job ID, poll exact status values, enforce timeout and retry policy, retrieve the private result, upload artifacts to Appwrite, and reconcile the canonical job as `COMPLETE` or `FAILED`.

The production queue worker remains a separate stage. It should be enabled only after private secret injection, Appwrite/Upstash connectivity, artifact retrieval, and failure-retry behavior have been validated. Camber Apps and the Science App Directory are explicitly prohibited for this worker.
