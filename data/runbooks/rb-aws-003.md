# S3 403 Forbidden — bucket policy, object ownership and KMS

Runbook ID: RB-AWS-003
Category: aws
Signals: S3 403 | S3 AccessDenied | s3:GetObject
Summary: S3 rejected the request because effective bucket/object access or KMS decryption permissions do not authorize the requesting role.
Sandbox commands: sentinel-sim inspect-s3-denial | sentinel-sim repair-reviewed-s3-policy

## Scope and safety
Private S3 object access, including cross-account uploads and SSE-KMS. A 403 does not prove that the object exists.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic application received S3 403 for newly uploaded SSE-KMS objects. The role could list an allowed prefix but lacked access to the upload key.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Record the caller role and sanitized request ID; compare bucket, object key prefix and region without exposing signed URLs.
2. Inspect bucket policy, role policy, ownership controls, endpoint policy and explicit deny conditions.
3. For SSE-KMS, inspect key policy and kms:Decrypt permission. With restricted ListBucket access, a missing object can also appear as 403.

## Root cause hypothesis
S3 rejected the request because effective bucket/object access or KMS decryption permissions do not authorize the requesting role. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-s3-denial` followed by `sentinel-sim repair-reviewed-s3-policy`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Prepare a scoped reviewed S3/KMS policy correction and request approval through the fixed simulation action.
2. Keep Block Public Access enabled. Do not grant public-read or broad bucket access to eliminate the symptom.
3. For a real rollout, canary the specific role and prefix before expanding the change.

## Validation and rollback
Success criteria: The intended role reads a canary object; an unrelated prefix and unauthorized role remain denied.

Rollback: Restore the prior policy version, including endpoint and KMS changes, and retain a safe canary object for diagnosis.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
Cross-account key access was absent from deployment tests. Add object ownership and KMS canary coverage.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
