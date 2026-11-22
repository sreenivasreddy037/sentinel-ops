"""Header-aware Qdrant dense/BM25 retrieval, RRF top 8, FlashRank top 3.

The explicit mock backend uses deterministic feature hashing + sparse term weights
and lexical reranking. It exercises Qdrant fusion but is NOT a semantic benchmark.
"""

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.config import Settings
from app.guardrails.pii_scrubber import scrub
from app.schemas import RetrievedDocument


def tokens(text: str) -> list[str]:
    return re.findall(r"[\w]+", text.lower())


def token_id(token: str) -> int:
    return int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "little")


@dataclass(frozen=True)
class Runbook:
    id: str
    title: str
    category: str
    summary: str
    signals: tuple[str, ...]
    commands: tuple[str, ...]
    text: str


def metadata_field(text: str, name: str, filename: str) -> str:
    match = re.search(rf"^{name}: (.+)$", text, re.MULTILINE)
    if match is None:
        raise ValueError(f"Missing {name} in {filename}")
    return match[1]


def read_runbooks(directory: Path) -> list[Runbook]:
    books = []
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")

        books.append(
            Runbook(
                id=metadata_field(text, "Runbook ID", path.name), title=text.splitlines()[0].removeprefix("# "),
                category=metadata_field(text, "Category", path.name), summary=metadata_field(text, "Summary", path.name),
                signals=tuple(metadata_field(text, "Signals", path.name).split(" | ")),
                commands=tuple(metadata_field(text, "Sandbox commands", path.name).split(" | ")),
                text=text,
            )
        )
    if not books or len({book.id for book in books}) != len(books):
        raise ValueError("Runbooks must have nonempty, unique IDs")
    return books


def markdown_chunks(book: Runbook) -> list[dict]:
    sections = re.split(r"(?m)(?=^## )", book.text)
    prefix = (
        f"{book.title}\nRunbook ID: {book.id}\nCategory: {book.category}\n"
        f"Signals: {' | '.join(book.signals)}\nSummary: {book.summary}\n"
        f"Allowed simulation commands (mutations require approval): {' | '.join(book.commands)}\n"
    )
    # Preserve each diagnostic procedure intact, never arbitrary token slicing.
    return [
        {
            "id": str(uuid5(NAMESPACE_URL, f"sentinel:{book.id}:{index}:{section}")),
            "runbook_id": book.id,
            "title": book.title,
            "text": prefix + section,
        }
        for index, section in enumerate(sections)
        if section.startswith("## ")
    ]


class HybridStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = settings.retrieval_backend
        self.collection = f"{settings.collection_name}_{self.backend}"
        if settings.qdrant_mode == "server":
            self.client = QdrantClient(url=settings.qdrant_url, timeout=30)
        elif settings.qdrant_mode == "memory":
            self.client = QdrantClient(location=":memory:")
        else:
            settings.qdrant_path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(settings.qdrant_path))
        self.books = {book.id: book for book in read_runbooks(settings.runbook_dir)}
        self.dense = self.sparse = self.reranker = None
        self.dimension = 256
        if self.backend == "fastembed":
            from fastembed import SparseTextEmbedding, TextEmbedding
            from flashrank import Ranker

            self.dense = TextEmbedding("BAAI/bge-small-en-v1.5", cache_dir=settings.model_cache)
            self.sparse = SparseTextEmbedding("Qdrant/bm25", cache_dir=settings.model_cache)
            self.reranker = Ranker(
                model_name="ms-marco-TinyBERT-L-2-v2", cache_dir=settings.model_cache
            )
            self.dimension = 384

    def close(self):
        self.client.close()

    def ensure_collection(self):
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                self.collection,
                vectors_config={
                    "dense": models.VectorParams(size=self.dimension, distance=models.Distance.COSINE)
                },
                sparse_vectors_config={
                    "bm25": models.SparseVectorParams(modifier=models.Modifier.IDF)
                },
            )

    def _mock_dense(self, text):
        vector = [0.0] * self.dimension
        for term, count in Counter(tokens(text)).items():
            vector[token_id(term) % self.dimension] += count
        norm = math.sqrt(sum(value * value for value in vector)) or 1
        return [value / norm for value in vector]

    def _mock_sparse(self, text, query=False):
        counts = Counter(tokens(text))
        values = {}
        for term, count in counts.items():
            # A small deterministic BM25-style test double; real backend uses FastEmbed BM25.
            values[token_id(term)] = 1.0 if query else count * 2.2 / (count + 1.2)
        indices = sorted(values)
        return models.SparseVector(indices=indices, values=[values[index] for index in indices])

    def ingest(self) -> dict:
        self.ensure_collection()
        chunks = [chunk for book in self.books.values() for chunk in markdown_chunks(book)]
        texts = [scrub(chunk["text"], self.settings.use_presidio).text for chunk in chunks]
        if self.backend == "fastembed":
            dense = [vector.tolist() for vector in self.dense.embed(texts)]
            sparse = [vector.as_object() for vector in self.sparse.embed(texts)]
        else:
            dense = [self._mock_dense(text) for text in texts]
            sparse = [self._mock_sparse(text) for text in texts]
        points = [
            models.PointStruct(
                id=chunk["id"], vector={"dense": dv, "bm25": sv},
                payload={**chunk, "text": text},
            )
            for chunk, text, dv, sv in zip(chunks, texts, dense, sparse, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)
        # Remove obsolete header chunks after content edits; upsert remains stable/idempotent.
        self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must_not=[models.HasIdCondition(has_id=[p.id for p in points])])
            ),
            wait=True,
        )
        return {"runbooks": len(self.books), "chunks": len(points), "backend": self.backend}

    def ready(self) -> bool:
        return self.client.collection_exists(self.collection) and self.client.count(
            self.collection, exact=True
        ).count > 0

    def search(self, query: str, limit: int = 3) -> list[RetrievedDocument]:
        if not self.ready():
            raise ValueError("Knowledge base is empty; call POST /ingest first")
        query = scrub(query, self.settings.use_presidio).text
        if self.backend == "fastembed":
            dense = next(self.dense.query_embed(query)).tolist()
            sparse = next(self.sparse.query_embed(query)).as_object()
        else:
            dense, sparse = self._mock_dense(query), self._mock_sparse(query, query=True)
        candidates = self.client.query_points(
            collection_name=self.collection,
            prefetch=[
                models.Prefetch(query=dense, using="dense", limit=8),
                models.Prefetch(query=sparse, using="bm25", limit=8),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=8, with_payload=True,
        ).points
        passages = [
            {"id": str(point.id), "text": point.payload["text"], "meta": point.payload}
            for point in candidates
        ]
        if self.backend == "fastembed":
            from flashrank import RerankRequest

            ranked = self.reranker.rerank(RerankRequest(query=query, passages=passages))
        else:
            query_tokens = set(tokens(query))
            for passage in passages:
                overlap = len(query_tokens & set(tokens(passage["text"])))
                passage["score"] = float(overlap) / max(len(query_tokens), 1)
            ranked = sorted(passages, key=lambda item: item["score"], reverse=True)
        return [
            RetrievedDocument(
                id=item["id"], runbook_id=item["meta"]["runbook_id"],
                title=item["meta"]["title"], text=item["text"], score=float(item["score"]),
            )
            for item in ranked[:limit]
        ]
