import json
from pathlib import Path

import pytest

from app.retrieval.hybrid_store import HybridStore, markdown_chunks, read_runbooks
from app.tools.remediation import actions_for

GOLDEN = json.loads(Path("evals/golden_set.json").read_text())


@pytest.mark.parametrize("query,expected", [
    ("0x80070005 Access Denied", "RB-ID-002"),
    ("HTTP 502 Bad Gateway", "RB-NET-002"),
    ("OOMKilled", "RB-LNX-003"),
])
def test_exact_codes_survive_hybrid_search(store, query, expected):
    docs = store.search(query)
    assert len(docs) == 3
    assert expected in {doc.runbook_id for doc in docs}
    assert query.split()[0].lower() in " ".join(doc.text.lower() for doc in docs)


@pytest.mark.parametrize("case", GOLDEN, ids=[case["id"] for case in GOLDEN])
def test_golden_retrieval_contract(store, case):
    found = {doc.runbook_id for doc in store.search(case["ticket"])}
    assert set(case["expected_runbook_ids"]) <= found


def test_header_chunks_preserve_full_diagnostic_section(settings):
    books = read_runbooks(settings.runbook_dir)
    assert len(books) == 15
    for book in books:
        chunks = markdown_chunks(book)
        assert len(chunks) == 7
        diagnostic = next(chunk for chunk in chunks if "## Diagnostic procedure" in chunk["text"])
        assert "1. " in diagnostic["text"] and "3. " in diagnostic["text"]
        assert all(book.id in chunk["text"] for chunk in chunks)


def test_ingest_is_idempotent(store):
    before = store.client.count(store.collection).count
    result = store.ingest()
    assert result["runbooks"] == 15
    assert store.client.count(store.collection).count == before == 105


def test_disk_qdrant_reopens_without_reingest(settings, tmp_path):
    local = settings.model_copy(update={"qdrant_mode": "local", "qdrant_path": tmp_path / "qdrant"})
    first = HybridStore(local)
    first.ingest()
    first.close()
    second = HybridStore(local)
    try:
        assert second.ready()
        assert second.search("0x80070005")[0].runbook_id == "RB-ID-002"
    finally:
        second.close()


def test_uses_two_qdrant_prefetches_and_rrf(store, monkeypatch):
    original = store.client.query_points
    captured = {}

    def query(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(store.client, "query_points", query)
    store.search("HTTP 502")
    assert [prefetch.using for prefetch in captured["prefetch"]] == ["dense", "bm25"]
    assert captured["query"].fusion.value == "rrf"
    assert captured["limit"] == 8


def test_runbook_command_metadata_matches_enforced_registry(settings):
    for book in read_runbooks(settings.runbook_dir):
        assert set(book.commands) == {action.command for action in actions_for(book.id)}
        assert all(command in markdown_chunks(book)[0]["text"] for command in book.commands)
