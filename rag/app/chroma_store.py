import json
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.models import BookDocument, QueryResult


class ChromaBookStore:
    """Pure-Python vector store backed by JSON + numpy files.

    Drop-in replacement for the previous ChromaDB-based store.
    Stores records in ``data/index.json`` and embeddings in ``data/vectors.npy``.
    """

    def __init__(self) -> None:
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._index_file = settings.chroma_path / "index.json"
        self._vectors_file = settings.chroma_path / "vectors.npy"
        self._lock = threading.Lock()

        # Strip "sentence-transformers/" prefix if present (local cache naming)
        model_name = settings.embedding_model.replace("sentence-transformers/", "", 1)
        self._model = SentenceTransformer(model_name)

        self._records: list[dict] = []
        self._vectors: np.ndarray | None = None
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._index_file.exists():
            with open(self._index_file, "r", encoding="utf-8") as f:
                self._records = json.load(f)
        if self._vectors_file.exists() and self._records:
            self._vectors = np.load(str(self._vectors_file))

    def _save(self) -> None:
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(self._records, f, ensure_ascii=False)
        if self._vectors is not None:
            np.save(str(self._vectors_file), self._vectors)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def upsert_books(self, books: list[BookDocument]) -> int:
        if not books:
            return 0

        texts = [book.to_document_text() for book in books]
        new_vectors = self._model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

        with self._lock:
            id_to_idx = {r["id"]: i for i, r in enumerate(self._records)}

            for i, book in enumerate(books):
                meta: dict = book.to_metadata()  # type: ignore[assignment]
                meta["id"] = book.id
                meta["document"] = texts[i]
                vec = new_vectors[i : i + 1]  # shape (1, dim)

                if book.id in id_to_idx:
                    idx = id_to_idx[book.id]
                    self._records[idx] = meta
                    if self._vectors is not None:
                        self._vectors[idx] = vec[0]
                else:
                    self._records.append(meta)
                    self._vectors = vec if self._vectors is None else np.vstack([self._vectors, vec])

            self._save()
        return len(books)

    def query(
        self,
        text: str,
        limit: int,
        year_from: int | None = None,
        year_to: int | None = None,
        material_type: str | None = None,
    ) -> list[QueryResult]:
        with self._lock:
            if not self._records or self._vectors is None:
                return []

            normalized_material_type = (material_type or "").strip().lower()

            # Apply year filter to select candidate indices
            candidates = [
                i
                for i, rec in enumerate(self._records)
                if (year_from is None or rec.get("year", 0) >= year_from)
                and (year_to is None or rec.get("year", 0) <= year_to)
                and (
                    not normalized_material_type
                    or normalized_material_type in str(rec.get("material_type", "")).lower()
                )
            ]
            if not candidates:
                return []

            query_vec = self._model.encode([text], convert_to_numpy=True)  # (1, dim)
            candidate_vecs = self._vectors[candidates]  # (n, dim)

            # Cosine similarity
            q_norm = query_vec / (np.linalg.norm(query_vec, axis=1, keepdims=True) + 1e-8)
            c_norm = candidate_vecs / (np.linalg.norm(candidate_vecs, axis=1, keepdims=True) + 1e-8)
            scores = (c_norm @ q_norm.T).flatten()  # (n,)

            top_k = min(limit, len(candidates))
            top_indices = np.argsort(scores)[::-1][:top_k]

            output: list[QueryResult] = []
            for idx in top_indices:
                rec = self._records[candidates[idx]]
                score = float(scores[idx])
                libraries_raw = str(rec.get("libraries", ""))
                document = str(rec.get("document", ""))
                summary = None
                for line in document.splitlines():
                    if line.startswith("Riassunto: "):
                        summary = line.replace("Riassunto: ", "", 1)
                        break
                output.append(
                    QueryResult(
                        id=str(rec.get("id", "")),
                        title=str(rec.get("title", "")),
                        author=str(rec.get("author", "")) or None,
                        year=int(rec.get("year", 0)) or None,
                        material_type=str(rec.get("material_type", "")) or None,
                        summary=summary,
                        libraries=[item.strip() for item in libraries_raw.split(" | ") if item.strip()],
                        available_copies=int(rec.get("available_copies", 0)) or None,
                        total_copies=int(rec.get("total_copies", 0)) or None,
                        source_url=str(rec.get("source_url", "")),
                        score=score,
                    )
                )
            return output

    def count(self) -> int:
        with self._lock:
            return len(self._records)
