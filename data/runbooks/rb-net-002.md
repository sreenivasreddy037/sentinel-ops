# HTTP 502 Bad Gateway — unhealthy or unreachable upstream

Runbook ID: RB-NET-002
Category: network
Signals: HTTP 502 | 502 Bad Gateway | upstream prematurely closed
Summary: A gateway could not obtain a valid response from its upstream; verify backend health, routing, protocol and connection limits.
Sandbox commands: sentinel-sim inspect-upstream-health | sentinel-sim restore-healthy-upstream

## Scope and safety
Reverse proxy or load balancer in front of a web service. A 502 is not interchangeable with a gateway timeout (504).

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic release pointed the proxy at a port no longer listening. Proxy logs showed connect() failed (111: Connection refused) and HTTP 502 Bad Gateway.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Correlate gateway request IDs and backend health checks around the first elevated 502 rate.
2. Inspect upstream address/port, readiness endpoints, proxy error logs and deployment changes. Check for refused versus reset connections.
3. Confirm protocol and TLS settings between proxy and backend, service endpoints, saturation and connection-pool limits.

## Root cause hypothesis
A gateway could not obtain a valid response from its upstream; verify backend health, routing, protocol and connection limits. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-upstream-health` followed by `sentinel-sim restore-healthy-upstream`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to restore a known healthy upstream or roll back the incompatible release in the sandbox simulation.
2. Canary a real routing change and preserve healthy capacity. Avoid indiscriminate restarts of every backend.
3. Adjust a timeout only if latency evidence justifies it; increasing limits can amplify overload.

## Validation and rollback
Success criteria: Canary and normal traffic return expected responses, 502 rates drop and backend health stays stable.

Rollback: Restore the prior upstream configuration and deployment revision; compare health and error rates during the rollback.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
The deployment checked process startup but not proxy-to-service connectivity. Add a routed readiness smoke test.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
