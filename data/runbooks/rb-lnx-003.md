# Linux or container memory pressure — OOMKilled and exit 137

Runbook ID: RB-LNX-003
Category: linux
Signals: OOMKilled | out of memory | exit 137
Summary: Memory consumption exceeded the process or container memory boundary; correlate the OOM event with limits and workload before selecting a fix.
Sandbox commands: journalctl -k --since -15min | systemctl restart sentinel-worker

## Scope and safety
Linux worker processes and container memory cgroups. Exit 137 alone can also result from an external SIGKILL.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic worker showed kernel oom-kill events during a larger batch. A container termination reason was OOMKilled and the recorded exit code was 137.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Inspect journalctl -k --since -15min for OOM evidence and identify whether the host or a cgroup hit its limit.
2. Compare working-set and RSS trends, container memory limits, node pressure, recent releases and concurrency settings.
3. Capture a safe memory profile where possible. Check for a leak versus a bounded but oversized batch; do not infer OOM solely from an exit code.

## Root cause hypothesis
Memory consumption exceeded the process or container memory boundary; correlate the OOM event with limits and workload before selecting a fix. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `journalctl -k --since -15min` followed by `systemctl restart sentinel-worker`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval for the fixed worker restart in the simulation. A restart is temporary containment, not a confirmed root-cause fix.
2. For a real change, reduce batch size/concurrency or revert a leaking release with capacity-owner approval.
3. Raise memory limits only after node capacity review. Do not turn off the OOM killer or remove all resource limits.

## Validation and rollback
Success criteria: The worker processes a representative batch without another OOM and memory headroom remains stable.

Rollback: Restore previous concurrency and resource settings if throughput or scheduling regresses; retain a canary rollback path.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
A load test omitted high-cardinality batches. Add memory profiling, representative data and alerts on RSS-to-limit ratio.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
