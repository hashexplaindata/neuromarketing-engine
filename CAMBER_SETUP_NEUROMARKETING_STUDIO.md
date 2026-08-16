# Neuromarketing Studio — Camber GPU Worker Setup

This document describes the safe setup path for the private Camber GPU worker used by **Neuromarketing Studio**. The procedure deliberately separates local preparation, Camber resource creation, smoke testing, and production integration.

## Architecture

```text
Neuromarketing Studio React client
        |
        v
Heroku authenticated API
        |
        v
Upstash queue and Appwrite job record
        |
        v
Camber GPU worker application
        |
        v
Appwrite result envelope and tenant-scoped visual artifacts
```

Heroku remains the lightweight API process. The Camber application owns GPU inference and must not be placed inside the Heroku web slug.

## Why a dedicated application is required

The existing Camber applications in the account are unrelated workloads or belong to other users. Neuromarketing Studio needs its own private application so that the command, container image, dependency set, GPU profile, and output contract are controlled by BIA.

## Local preparation

The repository contains the reviewable template:

```text
camber_app_definition.template.json
```

Before using it, replace the placeholder container image with an image that has actually been published and tested. The image must contain the repository source, `requirements-worker.txt`, pretrained model provisioning, and the `workers.camber_worker` entrypoint. Do not put API keys into the image or JSON definition.

The intended initial resource is one L4 GPU using the smallest GPU-capable profile. The account output identified `gpu_xsmall` as one XSMALL node with one L4 GPU, 8 CPUs, and 32 GB RAM. Increase to `gpu_small` only after measuring memory requirements and approving the additional cost.

## Camber-side creation

Run these commands from the user’s authenticated WSL Ubuntu terminal only after confirming the container image and resource pricing:

```bash
camber app create --file ~/neuromarketing-studio-app.json --output json
```

The command creates the application definition. It does not by itself prove that the worker image, Appwrite connectivity, or result contract works.

After creation, record the returned app identifier privately and inspect it without exposing credentials:

```bash
camber app describe <APP_IDENTIFIER> --output json
```

## Smoke-test gate

Do not run a real client asset first. Prepare a synthetic or public test asset in the Camber Stash and use a command that prints a deterministic success marker and writes a small result file. Confirm the exact job ID, status values, logs, and output path before connecting Signal Studio.

The production worker smoke test is a separate approval step because `camber app run` allocates compute:

```bash
camber app run <APP_IDENTIFIER> \
  --node-size XSMALL \
  --num-nodes 1 \
  --with-gpu \
  --output json
```

The exact positional app-identifier syntax must be confirmed against the installed CLI because the current help output does not display it. Do not guess the syntax or run the command until confirmed.

## Required evidence before integration

Capture the following non-secret values from the smoke job:

| Evidence | Required value |
|---|---|
| Application identifier | Camber app ID/name |
| Job identifier | Returned Camber job ID |
| Submission response | JSON response with status and timestamps |
| Status sequence | Exact queued, running, complete, and failed values |
| Logs | Command start, model load, completion, and error output |
| Output location | Stash path or result URL |
| GPU resource | Actual node/GPU selected |
| Runtime | Total duration and approximate memory usage |

## Production integration gate

Only after the smoke job succeeds should the provider adapter be connected to the Upstash queue. The adapter must persist the Camber job ID, poll exact status values, apply timeouts and retry policy, upload result artifacts to Appwrite, and mark the canonical job `COMPLETE` or `FAILED` deterministically.

The Camber API key must remain in environment configuration. It must never be committed to GitHub, embedded in a container image, copied into an app-definition file, or pasted into chat.
