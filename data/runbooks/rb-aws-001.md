# AWS IAM authorization failure — AccessDenied

Runbook ID: RB-AWS-001
Category: aws
Signals: IAM AccessDenied | not authorized to perform | AccessDeniedException
Summary: The effective IAM principal lacks an allowed action or is constrained by an explicit deny, boundary, session policy or organization SCP.
Sandbox commands: aws sts get-caller-identity | sentinel-sim iam-restore-reviewed-policy

## Scope and safety
AWS API authorization for a workload role. An administrator policy is not an acceptable incident shortcut.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic deployment changed the assumed role; CloudTrail showed AccessDeniedException and a different session issuer from the last successful request.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Confirm caller identity using aws sts get-caller-identity without printing temporary credentials.
2. Match the denied action, resource ARN, region, session issuer and request time to CloudTrail. Check identity and resource policies.
3. Evaluate permissions boundaries, SCPs, session restrictions and condition keys. An explicit deny overrides an allow.

## Root cause hypothesis
The effective IAM principal lacks an allowed action or is constrained by an explicit deny, boundary, session policy or organization SCP. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `aws sts get-caller-identity` followed by `sentinel-sim iam-restore-reviewed-policy`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Prepare the minimum reviewed action/resource permission or restore the intended role binding. Obtain security-owner approval.
2. Use only the fixed iam-restore-reviewed-policy simulation action; this project does not invoke IAM write APIs.
3. Avoid wildcard actions and resources. Separate credential compromise response from an ordinary missing permission.

## Validation and rollback
Success criteria: The same role performs the intended least-privilege operation, while a negative test for an unrelated resource still fails.

Rollback: Restore the prior versioned policy or trust relationship; revoke affected sessions if the security owner identifies compromise.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
The change pipeline checked policy syntax but not effective identity. Add role-identity assertions and least-privilege negative tests.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
