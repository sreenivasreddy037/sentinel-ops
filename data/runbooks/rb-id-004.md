# VPN RADIUS timeout — UDP reachability and authentication backend

Runbook ID: RB-ID-004
Category: identity
Signals: VPN RADIUS timeout | RADIUS timeout | RADIUS server not responding
Summary: The VPN gateway did not receive a timely RADIUS response; distinguish network loss, shared-secret mismatch and a slow authentication backend.
Sandbox commands: sentinel-sim inspect-radius-timeout | sentinel-sim restore-radius-route

## Scope and safety
VPN gateway to RADIUS/NPS authentication service, typically UDP 1812. A timeout is distinct from an explicit Access-Reject.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic firewall change blocked the return path from the RADIUS server. Gateway logs reported RADIUS server not responding during an otherwise healthy directory period.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Correlate gateway and RADIUS timestamps, approved client definitions and server health. Ensure clocks are synchronized.
2. Inspect UDP 1812 reachability and return traffic using approved metadata-only captures; do not log password attributes or shared secrets.
3. Check NPS/RADIUS event logs, MFA backend latency and shared-secret rotation metadata. Some invalid packets are silently discarded.

## Root cause hypothesis
The VPN gateway did not receive a timely RADIUS response; distinguish network loss, shared-secret mismatch and a slow authentication backend. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-radius-timeout` followed by `sentinel-sim restore-radius-route`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to restore the reviewed RADIUS route/firewall path in the fixed simulation.
2. If evidence supports a secret mismatch, coordinate a separate audited rotation on both ends; never paste the secret into the incident.
3. Do not bypass MFA or switch to an insecure authentication method to resolve a timeout.

## Validation and rollback
Success criteria: A verified canary authenticates through VPN and MFA, timeouts drop and unauthorized credentials still receive rejection.

Rollback: Restore the prior approved routing/rules and fail over only to an authorized secondary RADIUS service.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
Firewall regression tests omitted stateless authentication traffic. Add VPN canary probes and timeout-versus-reject monitoring.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
