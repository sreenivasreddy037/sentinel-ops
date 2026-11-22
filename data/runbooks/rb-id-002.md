# Windows 0x80070005 Access Denied — effective ACL or policy

Runbook ID: RB-ID-002
Category: identity
Signals: 0x80070005 | Windows Access Denied | E_ACCESSDENIED
Summary: Windows denied the requested operation under the current token, ACL, integrity level or policy; identify the exact denied object before changing permissions.
Sandbox commands: sentinel-sim inspect-windows-acl | sentinel-sim restore-reviewed-windows-acl

## Scope and safety
Windows file/service deployment operations. Error 0x80070005 is broad and does not by itself identify a broken ACL.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic deployment service lost Modify access to its dedicated application directory after a reviewed baseline was applied to the wrong path.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Record the exact operation and object path, the service identity, integrity level and effective access results.
2. Inspect inherited versus explicit ACLs, group membership and endpoint policy. Review Windows event evidence or an approved filtered Process Monitor capture.
3. Distinguish file permission problems from COM activation, Windows Update or policy restrictions; scope to the observed object.

## Root cause hypothesis
Windows denied the requested operation under the current token, ACL, integrity level or policy; identify the exact denied object before changing permissions. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-windows-acl` followed by `sentinel-sim restore-reviewed-windows-acl`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to restore the previously reviewed ACL on the specific sandbox application path.
2. For a real change, export the original ACL first and grant only the service identity the required rights.
3. Never grant Everyone Full Control or disable UAC to hide an access failure.

## Validation and rollback
Success criteria: The original operation succeeds under the intended service identity, while unrelated accounts remain denied.

Rollback: Restore the exported ACL and previous policy version; verify inheritance and stop if access becomes broader than intended.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
A baseline path selector matched the application directory unintentionally. Add effective-access tests and ACL diff review.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
