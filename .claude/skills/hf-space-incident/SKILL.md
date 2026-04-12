---
name: hf-space-incident
description: >
  Triage and recover this repo's Hugging Face Space when the service is unhealthy,
  the runtime is stuck, or the Space shows RUNTIME_ERROR, launch timeout, or
  branded 500s while the runtime API reports SLEEPING.
allowed-tools:
  - Read
  - Edit
  - Bash
---

# HF Space Incident

Use this skill for this repo when the user says the Hugging Face Space is unhealthy, timing out, stuck in `RUNTIME_ERROR`, returning branded `500` pages while the runtime reports `SLEEPING`, or failing health checks.

## Goal

Decide quickly whether this is:
- an app/container bug in this repo, or
- a stuck Hugging Face runtime that needs a restart

Then recover the service with the smallest reasonable action.

## Workflow

1. Inspect the repo assumptions first.
   - Read `Dockerfile`, `README.md`, and `backend/main.py`.
   - Confirm the Space is meant to serve on port `7860`.
   - Confirm `/health` exists and what it checks.

2. Check the live Space state before touching code.
   - Query `https://huggingface.co/api/spaces/lucharo/etymology/runtime`.
   - Query the public app host and `/health`.
   - Treat `HEAD /` carefully: it may return `404` even when `GET /` works.

3. Reproduce the app health locally.
   - Prefer a cheap local check first, for example:
     - `uv run python - <<'PY' ... from backend.main import health_check ... PY`
   - If local `/health` is healthy, assume the repo code is probably not the immediate problem.

4. Ensure Hugging Face tooling is available.
   - If `hf` is missing, install it with `uv tool install huggingface_hub`.
   - Verify auth with `hf auth whoami`.

5. Pull the useful HF diagnostics.
   - Runtime: `hf spaces info lucharo/etymology`
   - Logs:
     - `https://huggingface.co/api/spaces/lucharo/etymology/logs/run`
     - `https://huggingface.co/api/spaces/lucharo/etymology/logs/build`
   - The old `container` log endpoint may return `404`; prefer `run`.

6. Decide.
   - If run logs show Uvicorn started on `0.0.0.0:7860` and there is no traceback, while runtime is still unhealthy or stuck, treat it as an HF runtime issue.
   - If the public Space or custom domain returns a Hugging Face-branded `500` page while the runtime API reports `SLEEPING`, and local `/health` is healthy, treat that as an HF runtime-side recoverable outage rather than an app-code failure.
   - If local health fails or logs show a real traceback, fix the repo code first.

7. Recover with the smallest action.
   - For a likely HF runtime issue, restart the Space:
     - `from huggingface_hub import HfApi; HfApi().restart_space('lucharo/etymology')`
   - Poll until the runtime reaches `RUNNING` or `RUNTIME_ERROR`.

8. Verify recovery.
   - Check:
     - `https://lucharo-etymology.hf.space/`
     - `https://lucharo-etymology.hf.space/health`
     - `https://etymology.luischav.es/health`
   - Confirm the status page `latest.json` marks `etymology` as up.

9. If the status page still looks wrong, inspect monitor data rather than guessing.
   - The status page repo probes `https://etymology.luischav.es/health` with `GET`, not `HEAD`.
   - Use raw CSV history to confirm whether downtime was real:
     - `.../data/YYYY-MM.csv`

10. If guarded auto-recovery exists, validate it safely.
   - First inspect the exact trigger shape before assuming it will restart anything.
   - In the current status-page repo, the positive restart path is intentionally based on exact signal pairs, not broad heuristics:
     - `503 + RUNTIME_ERROR`
     - `500 + SLEEPING`
   - Safe production validation:
     - pause the Space,
     - confirm the app serves `503`,
     - confirm HF runtime reports `PAUSED`,
     - verify the recovery logic skips restart in that state.
   - For guard-path validation, watch worker logs directly with `wrangler tail`.
   - Do not assume `/recovery.json` will show a skipped restart; it mainly records actual recovery attempts and probe failures.
   - Do not try to force a real `RUNTIME_ERROR` in production just to test the positive restart branch.
   - Validate the positive branch locally or in a harness instead.

## Repo-specific notes

- The Space repo id is `lucharo/etymology`.
- The custom domain is `https://etymology.luischav.es`.
- The app health endpoint should return DB stats when healthy.
- Prefer restart over speculative code changes when:
  - local health is good,
  - logs show the server bound correctly,
  - and HF is the only failing layer.
- The status page auto-recovery is intentionally conservative:
  - two consecutive failures,
  - exact restart-eligible pairs:
    - `503 + RUNTIME_ERROR`
    - `500 + SLEEPING`
  - one-hour cooldown between restart attempts.

## Don’t over-engineer

- Do not redesign deployment on the first incident.
- If automatic recovery exists, keep it narrow and slow rather than broad and eager.
- First recover service, then verify whether there is any durable repo fix worth making.
