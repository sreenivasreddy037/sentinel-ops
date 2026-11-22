# Linux inode exhaustion — ENOSPC with free disk blocks

Runbook ID: RB-LNX-001
Category: linux
Signals: inode exhaustion | No space left on device | ENOSPC
Summary: A large population of tiny cache or spool files exhausted filesystem inodes even though block space remains; verify inode use before deleting anything.
Sandbox commands: df -i /var | logrotate -f /etc/logrotate.d/sentinel-demo

## Scope and safety
Linux ext4 /var on application workers; application writes fail while df -h can still show free space.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic incident began after a retry queue created one file per request. df -i reported IUse%=100%; df -h reported 61% block use. A recent deployment increased retry fan-out.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Run df -i /var and compare with df -h /var; identify the filesystem actually containing the failing path.
2. Use a bounded, low-priority directory inventory to locate cache, spool and rotated-log directories; avoid an unbounded find on a busy root filesystem.
3. Check ownership, retention policy, open deleted files and application retry rate. Preserve audit logs and customer uploads.

## Root cause hypothesis
A large population of tiny cache or spool files exhausted filesystem inodes even though block space remains; verify inode use before deleting anything. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `df -i /var` followed by `logrotate -f /etc/logrotate.d/sentinel-demo`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval for retention-based cleanup or reviewed log rotation; never recursively delete an arbitrary directory.
2. In the simulation, force only the dedicated sentinel-demo logrotate policy. In a real change, preview the policy and exclude active logs first.
3. Reduce the producer retry rate and apply queue retention limits. A filesystem redesign is a separate planned change.

## Validation and rollback
Success criteria: Inode utilization falls below 85%, a canary file can be created, and the application write-error rate returns to baseline.

Rollback: Restore retained files from the approved quarantine where supported. Deleted files are not assumed recoverable; stop if retention or ownership is uncertain.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
Detection lagged because alerting tracked bytes but not inodes. Add inode alerts, file-count budgets and a queue retention integration test.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
