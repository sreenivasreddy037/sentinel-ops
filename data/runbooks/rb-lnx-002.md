# systemd service crash — start-limit-hit and exit-code

Runbook ID: RB-LNX-002
Category: linux
Signals: systemd service crash | start-limit-hit | status=1/FAILURE
Summary: A service repeatedly exited after a configuration change, causing systemd start-rate limiting; inspect the first failure before considering a restart.
Sandbox commands: systemctl status sentinel-demo | systemctl restart sentinel-demo

## Scope and safety
A dedicated Linux sentinel-demo unit. A service restart can interrupt active requests and requires an owner-approved window.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic unit emitted status=1/FAILURE after an invalid configuration key. Later messages showed Start request repeated too quickly and Result=start-limit-hit.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Read systemctl status sentinel-demo and the unit journal around the FIRST crash, rather than only the final rate-limit message.
2. Inspect the rendered unit, EnvironmentFile permissions, WorkingDirectory, service account and recent configuration deployment.
3. Run the application configuration validator in a nonproduction context. Distinguish a missing dependency from an application startup exception.

## Root cause hypothesis
A service repeatedly exited after a configuration change, causing systemd start-rate limiting; inspect the first failure before considering a restart. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `systemctl status sentinel-demo` followed by `systemctl restart sentinel-demo`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Prepare a reviewed known-good configuration and request approval before changing a unit or restarting.
2. Restart only the fixed sandbox unit in this project. Real reset-failed or daemon-reload steps need separate review of the unit change.
3. Roll back the bad deployment if validation still fails; do not disable start-rate limits to hide a persistent crash.

## Validation and rollback
Success criteria: The unit remains active across the observation window and its readiness probe and error budget recover.

Rollback: Restore the previous unit/configuration version and coordinate a controlled restart. Retain the original journal for investigation.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
The release lacked a configuration schema check. Gate releases with config validation and alert on restart-rate changes.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
