# Understanding and presenting SentinelOps

## What you built

SentinelOps is an AI assistant for the first stage of IT incident response. It converts a messy ticket into a structured, cited investigation plan. It then waits for an operator before recording simulated corrective actions. Think of it as a careful on-call triage partner, with saved workflow state and an explicit human handoff.

Example: a ticket says “HTTP 502 Bad Gateway after deployment” and contains an email, IP address and password. SentinelOps removes the sensitive values, classifies the incident, looks up the gateway runbook, proposes a likely upstream failure and presents fixed diagnostic/remediation commands. Nothing mutating is recorded until a reviewer approves. A rejection ends the workflow without execution.

## Follow one ticket through the code

1. `app/main.py`: validates the HTTP request and creates a UUID thread. A service lock serializes work in the single-worker SQLite deployment.
2. `pii_scrubber.py`: removes covered secrets before graph input is saved. The first graph node checks it again. Originals are not stored in a reversible map.
3. `workflow.py`: a cheaper model selects severity, domain and focused retrieval queries. Mock mode uses deterministic rules.
4. `hybrid_store.py`: searches dense and sparse vectors in Qdrant, fuses eight candidates and reranks to three. Real mode uses FastEmbed/BM25/FlashRank; mock mode explicitly substitutes deterministic test vectors and ranking.
5. `workflow.py`: a reasoning model returns an `IncidentReport` through a Pydantic schema. Code verifies citations and command provenance, regardless of what the model claims.
6. If confidence is below 0.75 or citations are absent/invalid, the workflow rewrites the query at most twice. Continued uncertainty escalates with no executable plan.
7. `human_approval_gate`: LangGraph pauses using `interrupt()`. SQLite retains the thread. Approve or reject through a second API request, including after a restart.
8. `execute_remediation`: approved changes become durable simulation receipts. A deterministic idempotency key stops replay from recording the same action twice.

## Why this is more than a chatbot

A chatbot usually responds with text. This system has explicit state transitions, strict response contracts, evidence retrieval, bounded retries, stored checkpoints, approval/rejection rules, action provenance checks and an execution receipt ledger. Tests cover the handoff and failure paths; an evaluation harness measures the generated answer against expected evidence.

The retrieval knowledge base contains 15 synthetic runbooks. The golden set includes 20 tickets with expected runbook IDs and remediation strings. These provide a small reproducible starting point, not evidence of general enterprise incident coverage.

## Skills you can demonstrate

| Area | Concrete evidence |
|---|---|
| Agent engineering | LangGraph graph, conditional retry edges, durable interrupts and resume |
| RAG | Header-aware chunking, dense + BM25 named vectors, RRF and cross-encoder reranking |
| Model engineering | Separate classification and synthesis models; validated structured outputs |
| Safety | Pre-checkpoint redaction, fixed registry, mandatory approval for mutations, escalation |
| Backend engineering | Typed FastAPI endpoints, strict inputs, conflicts, optional bearer authentication |
| Reliability | SQLite checkpoints, persisted receipts, replay idempotency and restart tests |
| Quality | Offline contracts, 20 golden tickets, opt-in DeepEval thresholds and CI configuration |
| Delivery | uv project, non-root multi-stage image, API + Qdrant Compose stack |

## A short interview explanation

“I built SentinelOps to explore how an AI incident-response assistant can make useful recommendations while keeping humans in control. It retrieves runbooks using both semantic search and exact keyword matching, then produces a structured, cited hypothesis. LangGraph saves the workflow and pauses before a mutating action. Approval resumes it in a separate execution node. Execution is deliberately simulated with idempotent receipts. I also built offline safety tests and a 20-ticket evaluation harness so I can measure changes instead of relying on a convincing demo.”

If asked what is autonomous, say that classification, retrieval, query rewriting and report generation are automated. Mutating remediation requires a human. Do not describe it as an agent that independently repairs real infrastructure.

## Demo sequence

Run `MOCK_LLM=true uv run python scripts/demo_run.py`. Explain the redacted ticket, retrieved citation, proposed commands, empty execution log while paused, and receipt records after approval. Repeat with `approved=false` through the API. Then discuss why the execution node is separate: LangGraph replays the approval node on resume.

To demonstrate actual ML retrieval at no model API cost, run `MOCK_LLM=true RETRIEVAL_BACKEND=fastembed uv run python scripts/demo_run.py`. This downloads local models and requires connectivity. To demonstrate actual generation, use an OpenAI key and `MOCK_LLM=false`; API charges may apply.

## CV and LinkedIn wording

Implemented portfolio description:

“Implemented SentinelOps, a LangGraph incident-triage reference with Qdrant hybrid RAG, structured multi-model routing and human-approved remediation simulations; authored a 20-ticket evaluation harness and container/CI configuration.”

The offline suite, approval demo and container smoke test now pass in GitHub Actions. For real-model claims, add separately measured evidence. For example, report the exact golden-set hit rate and judge scores, the model versions and dataset size. Do not claim MTTR reduction, cost savings, production deployment or real remediation without evidence.

A LinkedIn post can show a short pause/approve/resume screen recording, the architecture and one measured failure case. The interesting engineering story is how you prevent a plausible answer from becoming an unsafe action.

## What remains before a production release

The offline gates and container smoke test pass, and `uv.lock` is committed. Before production, measure real retrieval/generation and add organizational authentication/reviewer roles. Horizontal scale needs shared persistence and distributed locking. Real remediation needs independently secured execution adapters, plan-bound approval and external idempotency. This repository intentionally leaves those as explicit deployment work.
