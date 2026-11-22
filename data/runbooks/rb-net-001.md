# DNS NXDOMAIN — missing record or negative cache

Runbook ID: RB-NET-001
Category: network
Signals: DNS NXDOMAIN | NXDOMAIN | DNS_PROBE_FINISHED_NXDOMAIN
Summary: The resolver returned a negative answer for the requested name; verify the authoritative zone, record spelling and negative cache lifetime.
Sandbox commands: dig app.example.test | sentinel-sim restore-reviewed-dns-record

## Scope and safety
Authoritative and recursive DNS for app.example.test. SERVFAIL and timeout have different failure paths.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic migration deleted the application CNAME before the replacement record propagated. Recursive resolvers retained a negative cached answer.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Compare dig app.example.test using the client resolver and the intended authoritative server.
2. Inspect the SOA negative caching TTL, split-horizon zone, recent change history and fully qualified record name.
3. Check whether search suffixes or DNSSEC validation changed the actual query. Distinguish NXDOMAIN from an empty NOERROR answer.

## Root cause hypothesis
The resolver returned a negative answer for the requested name; verify the authoritative zone, record spelling and negative cache lifetime. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `dig app.example.test` followed by `sentinel-sim restore-reviewed-dns-record`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to restore the reviewed DNS record through the simulation action.
2. In real DNS, publish the correct target and allow for positive and negative TTLs; avoid global resolver restarts.
3. Flush only an affected managed client cache when justified by evidence and client-owner approval.

## Validation and rollback
Success criteria: Authoritative and representative recursive resolvers return the expected record after the cache window.

Rollback: Restore the previous versioned zone entry, record the serial and recheck TTL behavior before another change.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
The cutover deleted the old record too early. Add a staged DNS migration checklist and synthetic resolution probes.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
