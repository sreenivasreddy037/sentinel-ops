# Verification record — November 22, 2026

## Result

**Offline acceptance verified in GitHub Actions.** [Run #2](https://github.com/sreenivasreddy037/sentinel-ops/actions/runs/45080430070), commit `2cf0be9650e584ab307ca76b78c8af511714b40a`, passed both the offline and container-smoke jobs. The public source and conventional commit history are published at [sreenivasreddy037/sentinel-ops](https://github.com/sreenivasreddy037/sentinel-ops).

| Check | Measured result |
|---|---|
| Dependency resolution/install | uv 0.9.11 on CPython 3.12.12; success |
| `uv run ruff check .` | All checks passed |
| Repository structure and interrupt boundary | Passed; 26 Python files, 15 runbooks, 20 golden tickets |
| `MOCK_LLM=true uv run pytest -v` | **66 passed, 21 skipped**, 2 dependency deprecation warnings; 5.23 seconds |
| Golden-ticket runbook retrieval | 20/20 cases passed with deterministic mock vectors and real local Qdrant fusion |
| Exact-code retrieval | All three tests passed: 0x80070005, HTTP 502, OOMKilled |
| Approval / rejection / restart / replay tests | Passed within the offline suite |
| End-to-end CLI demo | Passed: ingestion, redaction, cited RCA, interrupt pause, approval and simulation receipts |
| `docker compose config --quiet` | Passed |
| Multi-stage API image and Qdrant deployment | Built and started successfully in GitHub Actions |
| Container HTTP smoke | Passed against the real API + Qdrant server, including approval pause/resume |
| Real FastEmbed / FlashRank test | Not run; one opt-in model-download case skipped |
| Real OpenAI generation / DeepEval | Not run; 20 credential-dependent cases skipped |

Two pytest warnings came from the installed Sentry SDK through a development dependency. They were deprecation warnings, not failing tests. Offline mock scores are not semantic model benchmarks, production MTTR measurements or proof of real infrastructure recovery.

## Dependency lock and remote history

The CI-generated `uv.lock` was retrieved from the run artifact and committed. Local development, CI and Docker now use frozen installation. The follow-up workflow in [Actions](https://github.com/sreenivasreddy037/sentinel-ops/actions) verifies this frozen-install revision; the table above cites the completed baseline run rather than inventing results for a run in progress.

The first workflow run built and smoke-tested the container stack but found one Ruff import-spacing issue. That issue was corrected in a conventional test commit, and run #2 passed. The repository history includes separate docs, feature, test and CI commits, with subsequent verification fixes retained for review.

## Local environment limits

The original authoring sandbox still has Python 3.9.6, no uv or Docker, and blocked dependency downloads. Writing local `.git` metadata and `~/Desktop/SentinelOps` was rejected with `Operation not permitted`. Those restrictions did not prevent publishing through the connected GitHub service or testing on GitHub's hosted runners.

To obtain a normal local Git checkout, clone the published repository outside this sandbox. To create a source-only Desktop copy, run `python3 scripts/export_desktop.py` from an unrestricted local terminal. That exporter excludes credentials/runtime incident data and refuses to overwrite an existing folder.

## Additional local checks that passed

- Dependency-free AST parsing and bytecode compilation of all Python sources.
- `interrupt()` is outside every protected `try` body.
- 15 unique runbooks with seven intact header sections and at least 350 words each.
- 20 golden tickets with valid runbook IDs and remediation ground truth.
- 15 regex redaction examples, exact-code preservation, nonreversible metadata and repeat-scrub idempotence, including complete IPv4-mapped IPv6 redaction.
- Bash syntax for verification and Git initialization scripts; source ZIP integrity.

## Remaining quality and rollout work

Run real retrieval with `RUN_MODEL_TESTS=true MOCK_LLM=true uv run pytest -v -m models`. Run the real generation/judge cases with an OpenAI key and `RUN_LLM_EVALS=true`; record actual scores and model versions. The provided CI dispatch supports those checks, but they have not been represented as already passing.

Production exposure still needs organizational authentication/reviewer roles, per-thread authorization, retention controls and a reviewed execution adapter. Remediation remains sandbox simulation. See `docs/OPERATIONS.md` for the deployment boundary.
