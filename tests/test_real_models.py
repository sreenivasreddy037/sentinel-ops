"""Optional downloads: exercises real FastEmbed, BM25 and FlashRank without an API key."""

import os

import pytest

from app.retrieval.hybrid_store import HybridStore

pytestmark = [
    pytest.mark.models,
    pytest.mark.skipif(os.getenv("RUN_MODEL_TESTS") != "true",
                       reason="Set RUN_MODEL_TESTS=true to download real retrieval/reranker models"),
]


def test_real_hybrid_exact_identifiers(settings):
    real = settings.model_copy(update={"retrieval_backend": "fastembed"})
    store = HybridStore(real)
    try:
        store.ingest()
        for query, expected in [("0x80070005 Access Denied", "RB-ID-002"),
                                ("HTTP 502 Bad Gateway", "RB-NET-002"),
                                ("OOMKilled", "RB-LNX-003")]:
            assert expected in {doc.runbook_id for doc in store.search(query)}
    finally:
        store.close()
