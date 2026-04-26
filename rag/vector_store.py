from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings


class _EmbeddingAdapter(Embeddings):
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embedding_model.embed_query(text)


class VectorStoreManager:
    def __init__(self, index_dir: Path, embedding_model):
        self.index_dir = index_dir
        self.embedding_adapter = _EmbeddingAdapter(embedding_model)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def build_index(self, chunks: list[dict]) -> FAISS:
        deduped_chunks = self._dedupe_chunks_by_id(chunks)
        texts = [chunk["text"] for chunk in deduped_chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in deduped_chunks]
        ids = [chunk.get("id") for chunk in deduped_chunks]
        vector_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embedding_adapter,
            metadatas=metadatas,
            ids=ids,
        )
        vector_store.save_local(str(self.index_dir))
        return vector_store

    def has_index(self) -> bool:
        return (self.index_dir / "index.faiss").exists() and (self.index_dir / "index.pkl").exists()

    def incremental_update(self, changed_chunks: list[dict], remove_chunk_ids: list[str]) -> None:
        if not self.has_index():
            if changed_chunks:
                self.build_index(changed_chunks)
            return

        vector_store = self.load_index()
        deduped_changed_chunks = self._dedupe_chunks_by_id(changed_chunks)
        changed_ids = [chunk["id"] for chunk in deduped_changed_chunks if chunk.get("id")]
        existing_ids = self._existing_ids(vector_store)

        # Always treat changed IDs as replace operations: remove stale vectors first.
        ids_to_remove = list(dict.fromkeys([*remove_chunk_ids, *changed_ids]))
        ids_to_delete = [chunk_id for chunk_id in ids_to_remove if chunk_id in existing_ids]

        if ids_to_delete:
            try:
                vector_store.delete(ids=ids_to_delete)
            except Exception:
                pass

        if deduped_changed_chunks:
            # Re-check IDs after delete attempt; if deletion failed partially, skip existing IDs to avoid hard failures.
            existing_after_delete = self._existing_ids(vector_store)
            chunks_to_add = [
                chunk for chunk in deduped_changed_chunks if chunk.get("id") not in existing_after_delete
            ]

            texts = [chunk["text"] for chunk in chunks_to_add]
            metadatas = [chunk.get("metadata", {}) for chunk in chunks_to_add]
            ids = [chunk.get("id") for chunk in chunks_to_add]

            if texts:
                vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        vector_store.save_local(str(self.index_dir))

    @staticmethod
    def _dedupe_chunks_by_id(chunks: list[dict]) -> list[dict]:
        deduped: dict[str, dict] = {}
        without_id: list[dict] = []
        for chunk in chunks:
            chunk_id = chunk.get("id")
            if not chunk_id:
                without_id.append(chunk)
                continue
            deduped[chunk_id] = chunk
        return [*deduped.values(), *without_id]

    @staticmethod
    def _existing_ids(vector_store: FAISS) -> set[str]:
        id_map = getattr(vector_store, "index_to_docstore_id", {}) or {}
        return {str(doc_id) for doc_id in id_map.values() if doc_id is not None}

    def load_index(self) -> FAISS:
        return FAISS.load_local(
            str(self.index_dir),
            embeddings=self.embedding_adapter,
            allow_dangerous_deserialization=True,
        )
