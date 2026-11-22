"""Fixed action registry and durable, idempotent SANDBOX SIMULATION.

No subprocess, shell, SSH, cloud SDK mutation or arbitrary command execution exists.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from threading import RLock

from app.schemas import ExecutionRecord


@dataclass(frozen=True)
class Action:
    id: str
    runbook_id: str
    command: str
    mutating: bool


# Commands are portfolio examples. Targets are fixed sandbox resources.
ACTION_ROWS = [
    ("RB-LNX-001", "inode", "df -i /var", "logrotate -f /etc/logrotate.d/sentinel-demo"),
    ("RB-LNX-002", "systemd", "systemctl status sentinel-demo", "systemctl restart sentinel-demo"),
    ("RB-LNX-003", "oom", "journalctl -k --since -15min", "systemctl restart sentinel-worker"),
    ("RB-AWS-001", "iam", "aws sts get-caller-identity", "sentinel-sim iam-restore-reviewed-policy"),
    ("RB-AWS-002", "ssh", "sentinel-sim inspect-ec2-reachability", "sentinel-sim restore-approved-ssh-rule"),
    ("RB-AWS-003", "s3", "sentinel-sim inspect-s3-denial", "sentinel-sim repair-reviewed-s3-policy"),
    ("RB-NET-001", "dns", "dig app.example.test", "sentinel-sim restore-reviewed-dns-record"),
    ("RB-NET-002", "gateway", "sentinel-sim inspect-upstream-health", "sentinel-sim restore-healthy-upstream"),
    ("RB-NET-003", "tls", "sentinel-sim inspect-cert-expiry", "sentinel-sim deploy-renewed-certificate"),
    ("RB-K8S-001", "crashloop", "kubectl logs deploy/sentinel-demo --previous", "kubectl rollout undo deploy/sentinel-demo"),
    ("RB-K8S-002", "imagepull", "kubectl describe pod sentinel-demo", "sentinel-sim restore-known-image-digest"),
    ("RB-ID-001", "lockout", "sentinel-sim inspect-ad-lockout-events", "sentinel-sim unlock-verified-demo-account"),
    ("RB-ID-002", "winaccess", "sentinel-sim inspect-windows-acl", "sentinel-sim restore-reviewed-windows-acl"),
    ("RB-ID-003", "bitlocker", "sentinel-sim inspect-bitlocker-pcr", "sentinel-sim authorize-bitlocker-recovery"),
    ("RB-ID-004", "radius", "sentinel-sim inspect-radius-timeout", "sentinel-sim restore-radius-route"),
]
ACTIONS = {
    f"{name}_{kind}": Action(f"{name}_{kind}", runbook, command, mutating)
    for runbook, name, diagnostic, remediation in ACTION_ROWS
    for kind, command, mutating in [("diagnose", diagnostic, False), ("remediate", remediation, True)]
}
BY_COMMAND = {action.command: action for action in ACTIONS.values()}


def actions_for(runbook_id: str) -> list[Action]:
    return [action for action in ACTIONS.values() if action.runbook_id == runbook_id]


class SimulationExecutor:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.lock = RLock()
        connection.execute(
            "CREATE TABLE IF NOT EXISTS execution_receipts "
            "(idempotency_key TEXT PRIMARY KEY, receipt TEXT NOT NULL)"
        )
        connection.commit()

    def execute(self, thread_id: str, commands: list[str], approved: bool) -> list[dict]:
        # Validate the whole plan before persisting even a diagnostic receipt.
        if any(command not in BY_COMMAND for command in commands):
            raise ValueError("Action is outside the sandbox allowlist")
        plan = [BY_COMMAND[command] for command in commands]
        if any(action.mutating for action in plan) and not approved:
            raise PermissionError("Mutating simulation requires explicit human approval")
        receipts = []
        with self.lock, self.connection:
            for action in plan:
                key = hashlib.sha256(f"{thread_id}:{action.id}".encode()).hexdigest()
                existing = self.connection.execute(
                    "SELECT receipt FROM execution_receipts WHERE idempotency_key = ?", (key,)
                ).fetchone()
                if existing:
                    receipts.append(json.loads(existing[0]))
                    continue
                receipt = ExecutionRecord(
                    action_id=action.id,
                    command=action.command,
                    mutating=action.mutating,
                    result="SIMULATED: action recorded; no infrastructure was changed",
                    idempotency_key=key,
                ).model_dump()
                self.connection.execute(
                    "INSERT INTO execution_receipts VALUES (?, ?)", (key, json.dumps(receipt))
                )
                receipts.append(receipt)
        return receipts
