"""
ChromaDB vector store for semantic search and embeddings.

Stores meeting transcript chunks as embeddings for:
  - Semantic search across all meetings
  - Finding related meetings/content for connection detection
  - Pre-meeting briefing context retrieval
  - Insight generation context

Collections:
  - meeting_segments: Individual transcript segments with metadata
  - meeting_summaries: Executive summaries and topic summaries
"""

import logging
from pathlib import Path
from typing import Optional

from backend.config.settings import settings

logger = logging.getLogger(__name__)

CHROMA_DIR = settings.memory_dir.parent / "data" / "db" / "chromadb"


class VectorStore:
    """ChromaDB-backed vector store for semantic meeting search."""

    SEGMENTS_COLLECTION = "meeting_segments"
    SUMMARIES_COLLECTION = "meeting_summaries"

    def __init__(self, persist_dir: Optional[Path] = None):
        self._persist_dir = str(persist_dir or CHROMA_DIR)
        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._segments = self._client.get_or_create_collection(
                name=self.SEGMENTS_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._summaries = self._client.get_or_create_collection(
                name=self.SUMMARIES_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info(
                f"VectorStore initialized: "
                f"{self._segments.count()} segments, "
                f"{self._summaries.count()} summaries"
            )
        except Exception as e:
            logger.warning(f"ChromaDB unavailable, vector search disabled: {e}")
            self._client = None
            self._segments = None
            self._summaries = None
            self._available = False

    def add_segments(
        self,
        meeting_id: str,
        segments: list[dict],
    ):
        """
        Store transcript segments as embeddings.

        Each segment dict should have:
          - id: unique segment ID
          - text: transcript text
          - start_time: float
          - end_time: float
          - speaker: optional speaker name
        """
        if not self._available or not segments:
            return

        ids = []
        documents = []
        metadatas = []

        for seg in segments:
            seg_id = f"{meeting_id}_{seg['id']}"
            ids.append(seg_id)
            documents.append(seg["text"])
            metadatas.append({
                "meeting_id": meeting_id,
                "segment_id": seg["id"],
                "start_time": seg.get("start_time", 0.0),
                "end_time": seg.get("end_time", 0.0),
                "speaker": seg.get("speaker", "Unknown"),
            })

        self._segments.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Stored {len(ids)} segments for meeting {meeting_id[:8]}")

    def add_summary(
        self,
        meeting_id: str,
        summary_type: str,
        text: str,
        metadata: Optional[dict] = None,
    ):
        """
        Store a summary (executive summary, topic summary, etc.).

        summary_type: "executive" | "topic" | "action_items" | "decisions"
        """
        if not self._available or not text.strip():
            return

        doc_id = f"{meeting_id}_{summary_type}"
        meta = {
            "meeting_id": meeting_id,
            "summary_type": summary_type,
        }
        if metadata:
            meta.update(metadata)

        self._summaries.upsert(ids=[doc_id], documents=[text], metadatas=[meta])

    def search_segments(
        self,
        query: str,
        n_results: int = 10,
        meeting_id: Optional[str] = None,
    ) -> list[dict]:
        """Semantic search across transcript segments."""
        if not self._available:
            return []
        where = {"meeting_id": meeting_id} if meeting_id else None

        results = self._segments.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return self._format_results(results)

    def search_summaries(
        self,
        query: str,
        n_results: int = 5,
        summary_type: Optional[str] = None,
    ) -> list[dict]:
        """Semantic search across meeting summaries."""
        if not self._available:
            return []
        where = {"summary_type": summary_type} if summary_type else None

        results = self._summaries.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        return self._format_results(results)

    def find_related_meetings(
        self,
        query: str,
        exclude_meeting_id: Optional[str] = None,
        n_results: int = 5,
    ) -> list[dict]:
        """
        Find meetings related to a query by searching summaries.
        Returns unique meeting IDs with relevance scores.
        """
        if not self._available:
            return []
        results = self._summaries.query(
            query_texts=[query],
            n_results=n_results * 2,
            include=["metadatas", "distances"],
        )

        meetings = {}
        if results["metadatas"] and results["distances"]:
            for meta, distance in zip(results["metadatas"][0], results["distances"][0]):
                mid = meta.get("meeting_id", "")
                if mid == exclude_meeting_id:
                    continue
                relevance = 1.0 - distance  # cosine distance to similarity
                if mid not in meetings or relevance > meetings[mid]["relevance"]:
                    meetings[mid] = {
                        "meeting_id": mid,
                        "relevance": round(relevance, 3),
                        "summary_type": meta.get("summary_type", ""),
                    }

        sorted_meetings = sorted(
            meetings.values(), key=lambda x: x["relevance"], reverse=True
        )
        return sorted_meetings[:n_results]

    def get_meeting_context(
        self,
        meeting_id: str,
    ) -> list[dict]:
        """Get all stored content for a specific meeting."""
        if not self._available:
            return []
        seg_results = self._segments.get(
            where={"meeting_id": meeting_id},
            include=["documents", "metadatas"],
        )
        sum_results = self._summaries.get(
            where={"meeting_id": meeting_id},
            include=["documents", "metadatas"],
        )

        context = []
        if seg_results["documents"]:
            for doc, meta in zip(seg_results["documents"], seg_results["metadatas"]):
                context.append({"type": "segment", "text": doc, **meta})
        if sum_results["documents"]:
            for doc, meta in zip(sum_results["documents"], sum_results["metadatas"]):
                context.append({"type": "summary", "text": doc, **meta})

        return context

    def delete_meeting(self, meeting_id: str):
        """Remove all embeddings for a meeting."""
        if not self._available:
            return
        seg_results = self._segments.get(
            where={"meeting_id": meeting_id},
        )
        if seg_results["ids"]:
            self._segments.delete(ids=seg_results["ids"])

        sum_results = self._summaries.get(
            where={"meeting_id": meeting_id},
        )
        if sum_results["ids"]:
            self._summaries.delete(ids=sum_results["ids"])

        logger.info(f"Deleted embeddings for meeting {meeting_id[:8]}")

    def stats(self) -> dict:
        if not self._available:
            return {"segments_count": 0, "summaries_count": 0, "available": False}
        return {
            "segments_count": self._segments.count(),
            "summaries_count": self._summaries.count(),
            "available": True,
        }

    def _format_results(self, results: dict) -> list[dict]:
        formatted = []
        if not results["documents"]:
            return formatted

        for i, (doc, meta, dist) in enumerate(
            zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ):
            formatted.append({
                "text": doc,
                "relevance": round(1.0 - dist, 3),
                **meta,
            })
        return formatted


# Lazy singleton — initialized on first access
_vector_store_instance: Optional[VectorStore] = None


def _get_vector_store() -> VectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


class _VectorStoreProxy:
    """Proxy that lazily initializes VectorStore on first attribute access."""

    def __getattr__(self, name):
        return getattr(_get_vector_store(), name)


vector_store = _VectorStoreProxy()
