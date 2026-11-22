# Operations and deployment limits

## Trust boundaries

SentinelOps is a local-first, single-worker reference. The API classifies incidents and proposes hypotheses; it never confirms production recovery. All registered commands are strings converted into simulated execution receipts. There is no shell, cloud write client or subprocess executor.

Tickets, runbooks and model responses are untrusted. A system prompt rejects embedded instructions, but prompt text is not a complete security boundary. The fixed action registry, citation/provenance checks, human gate and absence of a real executor are the enforceable boundaries.

The privacy scrubber covers IPv4, IPv6, emails, AKIA/ASIA keys, common password/secret/token assignments, bearer tokens, PEM private keys and a pattern-only Presidio telephone recognizer. It is not a universal DLP or person-name detector. Add organization-specific identifiers and adversarial tests before handling real incidents. Unlabeled secrets may evade pattern detection.

The original incident is sanitized before graph.invoke: a checkpointer saves input before the first node runs. Thus `raw_ticket` is intentionally a sanitized compatibility field, and `redaction_map` maps placeholders to types rather than originals. Approval notes are likewise scrubbed before `Command(resume=...)`. API validation errors exclude raw input; exception responses and application logs exclude exception text and request bodies.

## Exposure, identity and persistence

- Compose binds API port 8000 to loopback and does not expose Qdrant to the host.
- Set a high-entropy `API_TOKEN` for shared use. Add TLS, organizational SSO, separate triage/reviewer roles, per-thread authorization, request limits and a durable reviewer identity audit before network exposure.
- Do not log request bodies or forward full payloads through tracing callbacks. Langfuse is opt-in and receives metadata only.
- Keep one API worker. The process-local lock is not a cross-process approval lock. SQLite serializes storage writes but does not implement a distributed approval claim.
- Named volumes retain sanitized checkpoints, simulation receipts, model cache and Qdrant vectors. Treat sanitized incidents as confidential: use encrypted storage, backups, restricted access and a retention/deletion policy.
- The runtime is non-root, drops capabilities and has a read-only root filesystem with dedicated writable volumes. Qdrant should receive its own hardened image policy before a shared production deployment.

## Startup and readiness

The health endpoint is liveness. `/ready` verifies the indexed knowledge store. With `AUTO_INGEST=true` (default), lifespan startup indexes runbooks before serving requests and retries a briefly unavailable store. Set `AUTO_INGEST=false` only if you deliberately manage indexing yourself. Qdrant's Compose dependency is `service_started`; startup retries indexing while Qdrant initializes. Persistent dependency failures stop API startup instead of silently claiming readiness. Model mode downloads the embedding/reranking assets on first initialization; bake or warm the cache for a controlled rollout.

A practical starting point is 2 CPU cores and 4 GB RAM for the API plus Qdrant, then measure memory under real models and concurrency. These are planning estimates, not tested hardware requirements. Mock mode is much lighter. Container integration needs a Docker engine; Compose syntax validation alone does not establish that the images build or services work.

## Recovery and idempotency

A pending approval survives an API restart when the SQLite volume remains intact. Inspect `GET /threads/{id}`; resume the same pending thread through `/approve/{id}`. Approving an already completed/denied/escalated thread returns 409. An unsupported command or citation causes a bounded retrieval retry and eventual escalation.

The execution receipt transaction is idempotent for each `(thread_id, action_id)`. This guarantees one stored simulation receipt per action across execution-node replay; it does not claim exactly-once delivery to a future remote infrastructure provider. Receipt writes and graph checkpoints use independent SQLite connections and transactions; replay reconciles by receipt key.

If an exception leaves a thread at a non-approval node, inspect sanitized state and service logs. There is intentionally no public arbitrary replay endpoint. A trusted operator may resume the compiled graph with `invoke(None, config)` under the same service lock after diagnosing the failure. Back up the database first and never modify checkpoint tables manually.

## Before enabling real execution

Implement typed adapters with fixed resource scopes, IAM least privilege, preflight checks, timeouts, provider-side idempotency and verification/rollback. Approval must bind an authenticated reviewer to an immutable plan hash, target, scope and expiry. Include external-provider reconciliation for crashes between side effects and checkpointing. Retain diagnostics as read-only tools. Add sandbox escape tests and separate production execution credentials from the model process.

## Reproducibility and releases

The committed `uv.lock` was generated by GitHub Actions on Python 3.12.12. Local development, CI and the Docker builder use frozen installation. Update dependencies explicitly, rerun the complete gates, and commit the reviewed lockfile change. Before release, pin base images/actions by digest or commit SHA and run dependency/image vulnerability scans. Do not state that those checks already passed.

The GitHub workflow includes paid semantic evaluation only on explicit dispatch. To prevent prompt regressions in a release process, make that job required for prompt/model changes or run a secrets-enabled protected evaluation workflow. Keep fork PR jobs unprivileged and avoid exposing secrets to untrusted code.
