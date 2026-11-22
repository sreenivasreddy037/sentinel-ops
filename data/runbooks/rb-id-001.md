# Active Directory account lockout — event 4740 and 0xC0000234

Runbook ID: RB-ID-001
Category: identity
Signals: Active Directory lockout | event 4740 | 0xC0000234 | account locked out
Summary: Repeated failed authentication locked the account; identify the source and validate the user before unlocking.
Sandbox commands: sentinel-sim inspect-ad-lockout-events | sentinel-sim unlock-verified-demo-account

## Scope and safety
Windows domain identity. A lockout can indicate stale service credentials or an active attack.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic domain controller logged event 4740 for a demo account. A scheduled task continued using an old password after a legitimate rotation.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Correlate domain-controller lockout event 4740, caller computer and nearby failed logon events without exposing credentials.
2. Inspect scheduled tasks, mapped drives, cached credentials, services and mobile clients on the identified source.
3. Escalate suspicious sources or spray patterns to security. Do not contact or unlock an identity without the approved verification process.

## Root cause hypothesis
Repeated failed authentication locked the account; identify the source and validate the user before unlocking. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-ad-lockout-events` followed by `sentinel-sim unlock-verified-demo-account`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval after identity verification for the fixed demo-account unlock simulation.
2. In a real change, update the stale credential through secret management or stop the offending task before unlocking.
3. Do not relax the domain lockout threshold or repeatedly unlock an account while an attack continues.

## Validation and rollback
Success criteria: The verified account authenticates and no new lockout events occur from the old source during observation.

Rollback: Disable the verified offending task or re-lock the account with security-owner approval if suspicious activity resumes.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
The password rotation inventory missed a scheduled task. Add service-account ownership and credential-use inventory.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
