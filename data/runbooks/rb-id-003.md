# BitLocker recovery trigger — TPM/PCR measurement change

Runbook ID: RB-ID-003
Category: identity
Signals: BitLocker recovery | PCR validation | TPM recovery
Summary: Boot integrity measurements or TPM state changed, so BitLocker requires recovery; verify device identity and authorized firmware changes first.
Sandbox commands: sentinel-sim inspect-bitlocker-pcr | sentinel-sim authorize-bitlocker-recovery

## Scope and safety
Managed Windows devices with escrowed recovery keys. Recovery keys must never enter tickets, chat, logs or source control.

These are synthetic training incidents, not records of a real outage. All commands in SentinelOps execute only as sandbox receipts. Confirm impact, affected scope and change ownership before a real operator takes action.

## Symptoms and error evidence
The synthetic laptop entered recovery after a firmware update changed measured boot state. Device management showed the expected device owner and change window.

Preserve timestamps and sanitized request/event IDs. Treat one symptom as evidence to investigate, not proof of a single cause.

## Diagnostic procedure
1. Confirm asset identity and user identity through approved channels; inspect firmware/boot changes and TPM/PCR evidence.
2. Check the management system for key escrow and recovery policy without copying a recovery secret into SentinelOps.
3. Escalate unexplained boot changes or physical tampering to security. Do not assume every recovery prompt is a routine firmware event.

## Root cause hypothesis
Boot integrity measurements or TPM state changed, so BitLocker requires recovery; verify device identity and authorized firmware changes first. Correlate this hypothesis with the diagnostic results and the most recent authorized change. If the evidence contradicts it, stop and retrieve additional context rather than executing the proposed plan.

## Remediation and approval
Fixed simulation plan: `sentinel-sim inspect-bitlocker-pcr` followed by `sentinel-sim authorize-bitlocker-recovery`. The second action is mutating and requires human approval. These commands are recorded as simulation receipts, never executed by a shell.

1. Request approval for the simulated authorization step only. This project cannot retrieve or enter a BitLocker key.
2. A verified operator uses the separate audited recovery workflow and follows policy for re-sealing or key rotation.
3. Do not disable encryption or clear the TPM as an incident shortcut.

## Validation and rollback
Success criteria: The verified device boots through the approved process, protection is enabled and audit/escrow records are current.

Rollback: Stop the recovery workflow if identity or device integrity cannot be verified; retain encryption and involve endpoint security.

Record before/after evidence and the change approver. Recovery must be verified by real monitoring; a successful simulation is not production recovery.

## Synthetic post-mortem and prevention
Firmware rollout lacked a staged recovery readiness check. Add escrow verification and documented endpoint-owner approval.

The incident owner should document the detection gap, contributing change, remediation evidence and follow-up owner. An incomplete RCA should remain a hypothesis until independently validated.
