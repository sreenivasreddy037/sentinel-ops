# Verification record — November 22, 2026

## Downloadable project acceptance

[GitHub Actions run #8](https://github.com/sreenivasreddy037/sentinel-ops/actions/runs/45083283534), code commit `ba271bfe9fb455014daeca808c3569985052ea39`, completed successfully. All five non-paid jobs passed. The optional paid OpenAI/DeepEval job was deliberately skipped because no API credential was supplied.

| Check | Measured result |
|---|---|
| Frozen dependencies | uv 0.9.11; managed CPython 3.12.12 |
| Ruff | All checks passed |
| Offline Python suite | **74 passed, 21 optional cases skipped**, 5.58 seconds on the Linux runner |
| Real retrieval/reranking | FastEmbed dense + BM25 + FlashRank: all three exact-code queries passed |
| Golden retrieval contracts | 20/20 mock-vector cases found their expected runbook IDs |
| First-start behavior | Automatic indexing, `/ready`, dashboard assets and startup retry tests passed |
| Browser workflow | Analyze → redacted ticket → approval → two simulation receipts; rejection and escalation also passed, with no browser errors |
| Native Linux launch | Actual localhost server, automatic indexing and approval lifecycle passed |
| Native Windows launch | Distribution tests and actual first-start HTTP workflow passed |
| Native Apple silicon Mac launch | Distribution tests and actual first-start HTTP workflow passed |
| Prepared Mac bundle | Built, extracted to a different directory, then passed lint, full tests, CLI demo and native HTTP smoke |
| Docker distribution | Multi-stage image built; API + Qdrant started; dashboard/readiness and approval HTTP smoke passed |
| Compose syntax | Passed |
| Paid generation/judge scores | 20 cases not run; user API key is required |

The full offline suite skips one model-download case and 20 paid judge cases. The separate `retrieval-models` job runs the real model-download case, so retrieval is independently verified. Mock-vector golden-set results are not presented as semantic quality scores.

## Prepared Mac download

The successful run publishes a `SentinelOps-macos-arm64` artifact containing source, a relocatable managed Python runtime, uv and the locked dependencies. It is tested after moving to a new extraction directory. Artifacts are retained for 30 days and can require a GitHub sign-in; the public source ZIP and native launcher are the permanent distribution path.

Source users need Python 3.9+ with pip and internet for the first bootstrap. The launcher installs Python 3.12 and project dependencies locally. Docker is optional. See `docs/GETTING_STARTED.md`.

## Reliability checks

Execution receipts now use a separate SQLite connection from background LangGraph checkpoints. A regression test proves a receipt commit cannot end an active checkpoint transaction. The full workflow suite passed after this fix.

The launcher retains the base interpreter of an existing Python 3.12 environment rather than replacing an active Windows virtualenv. The prepared Mac bundle includes its binary tools, uses managed standalone Python rather than a machine-specific framework installation, and excludes bundled dependencies from source linting. Both native platforms passed after these corrections.

One Docker build encountered an external PyPI download timeout. Download timeouts/retries were adjusted and the final complete Docker build and smoke test passed. The final successful run is the verification baseline linked above.

## Additional local validation

The prepared Apple silicon runtime was also checked locally: Python 3.12.12 and uv 0.9.11 version checks, Ruff, **74 Python tests with 21 optional skips**, and the full CLI approval demo passed. Unrelated pytest plugin autoload was disabled for this local invocation; CI used the standard test invocation.

The native launcher is `bash start.sh`, `start.cmd` on Windows, or `Start-SentinelOps.command` on Mac. First-time setup and environment requirements are documented in `docs/GETTING_STARTED.md`.

## Production boundary

The current release provides incident triage, reviewed plans and simulation-only remediation. Real OpenAI mode requires an API key; paid generation and judge evaluations have not yet run. Organizational SSO/reviewer roles, per-thread authorization, production retention controls and real infrastructure execution adapters remain separate rollout work. See `docs/OPERATIONS.md`.
