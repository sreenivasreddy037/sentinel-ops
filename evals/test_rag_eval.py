"""Paid, opt-in judge metrics on REAL retrieval and REAL generated responses.

When an API key is available this runs unless RUN_LLM_EVALS=false is explicitly set.
Default offline CI skips cleanly rather than substituting mock semantic scores.
"""

import json
import os
from pathlib import Path

import pytest

from app.config import Settings
from app.graph.workflow import ModelRouter
from app.retrieval.hybrid_store import HybridStore

GOLDEN = json.loads(Path(__file__).with_name("golden_set.json").read_text())
ENABLED = bool(os.getenv("OPENAI_API_KEY")) and os.getenv("RUN_LLM_EVALS", "true").lower() == "true"
pytestmark = [
    pytest.mark.online,
    pytest.mark.skipif(not ENABLED,
                       reason="Paid RAG eval skipped: OPENAI_API_KEY required; RUN_LLM_EVALS must not be false"),
]


@pytest.fixture(scope="module")
def real_rag():
    settings = Settings(
        _env_file=None, mock_llm=False, retrieval_backend="fastembed", qdrant_mode="memory",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
    store = HybridStore(settings)
    store.ingest()
    yield store, ModelRouter(settings, store)
    store.close()


@pytest.mark.parametrize("case", GOLDEN, ids=[case["id"] for case in GOLDEN])
def test_rag_quality_gate(real_rag, case):
    from deepeval.metrics import ContextualRecallMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    store, router = real_rag
    docs = store.search(case["ticket"])
    state = {"scrubbed_ticket": case["ticket"], "retrieved_docs": [doc.model_dump() for doc in docs]}
    report = router.synthesize(state)
    test_case = LLMTestCase(
        input=case["ticket"],
        actual_output=report.root_cause + "\nProposed simulation: " + "; ".join(report.proposed_commands),
        expected_output=case["expected_answer"],
        retrieval_context=[doc.text for doc in docs],
    )
    # Explicit local scores form a CI gate; never upload incident examples to DeepEval SaaS.
    faithfulness = FaithfulnessMetric(threshold=0.85, model="gpt-4o-mini", async_mode=False)
    recall = ContextualRecallMetric(threshold=0.80, model="gpt-4o-mini", async_mode=False)
    faithfulness.measure(test_case)
    recall.measure(test_case)
    assert faithfulness.score >= 0.85, faithfulness.reason
    assert recall.score >= 0.80, recall.reason
    assert set(case["expected_runbook_ids"]) <= {doc.runbook_id for doc in docs}
    assert case["ground_truth_remediation"] in report.proposed_commands
