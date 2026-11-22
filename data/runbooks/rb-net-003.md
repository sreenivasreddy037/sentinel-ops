# TLS certificate expired — CERT_HAS_EXPIRED

Runbook ID: RB-NET-003
Category: network
Signals: TLS cert expired | CERT_HAS_EXPIRED | certificate has expired
Summary: The served certificate or an intermediate is outside its validity period; inspect the complete chain and deployment target.
Sandbox commands: sentinel-sim inspect-cert-expiry | sentinel-sim deploy-renewed-certificate

## Scope and safety
Public or internal TLS endpoints. Never disable certificate verification as a remediation.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic renewal succeeded in the secret store but the ingress still served the previous leaf certificate. Clients reported certificate has expired.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Inspect notBefore/notAfter, subject names and the complete chain served using the intended SNI name.
2. Verify system time and compare the certificate at the load balancer, ingress and source secret store.
3. Check renewal job status, issuer events, deployment propagation and permissions to read the renewed certificate.

## Root cause hypothesis
The served certificate or an intermediate is outside its validity period; inspect the complete chain and deployment target. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-cert-expiry` followed by `sentinel-sim deploy-renewed-certificate`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to deploy the renewed certificate and correct chain using the fixed simulation.
2. Use the approved issuer and secret distribution process. Never include private keys in a ticket or repository.
3. Reload only the affected listener when supported, canary the new chain, and preserve a known-valid fallback.

## Validation and rollback
Success criteria: Representative clients trust the full chain, hostname validation succeeds and expiration monitoring sees the new date.

Rollback: Restore a still-valid previous certificate if the new deployment breaks compatibility; an expired certificate is not a viable recovery target.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
Monitoring watched issuance but not the certificate actually served. Add endpoint expiry probes and renewal propagation checks.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
