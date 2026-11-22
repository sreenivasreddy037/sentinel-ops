# EC2 SSH timeout — network path versus authentication

Runbook ID: RB-AWS-002
Category: aws
Signals: EC2 SSH timeout | ssh: connect to host | port 22: Connection timed out
Summary: The SSH TCP path is unreachable because of routing, security groups, NACLs or host reachability; a timeout is distinct from Permission denied.
Sandbox commands: sentinel-sim inspect-ec2-reachability | sentinel-sim restore-approved-ssh-rule

## Scope and safety
EC2 access through an approved bastion or corporate network. Never open port 22 to the whole internet as a shortcut.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic maintenance change removed the approved bastion source range from a security group. Reachability checks failed before authentication.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Compare EC2 status checks, target subnet, destination address and the approved bastion connection path.
2. Inspect security-group ingress, stateful return traffic, NACL rules and stateless ephemeral-port return paths.
3. Check routes, VPN/bastion health and host firewall. Use read-only reachability analysis; do not paste private keys into tickets.

## Root cause hypothesis
The SSH TCP path is unreachable because of routing, security groups, NACLs or host reachability; a timeout is distinct from Permission denied. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-ec2-reachability` followed by `sentinel-sim restore-approved-ssh-rule`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval to restore the specific reviewed bastion source rule in the simulation.
2. A real change must record the previous security-group rule and have an expiry or configuration-as-code owner.
3. If instance checks fail, involve the compute owner before reboot or volume repair. Authentication errors need a different investigation.

## Validation and rollback
Success criteria: The bastion establishes TCP/SSH connectivity and unauthorized source networks remain blocked.

Rollback: Revert the exact network rule change and use an approved break-glass path if access remains unavailable.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
A network policy deployment omitted a bastion regression test. Add source-restricted reachability checks to the release gate.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
