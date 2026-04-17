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
        texts = [chunk["text"] for chunk in chunks]
        metadatas = [chunk.get("metadata", {}) for chunk in chunks]
        ids = [chunk.get("id") for chunk in chunks]
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

        if remove_chunk_ids:
            try:
                vector_store.delete(ids=remove_chunk_ids)
            except Exception:
                pass

        if changed_chunks:
            texts = [chunk["text"] for chunk in changed_chunks]
            metadatas = [chunk.get("metadata", {}) for chunk in changed_chunks]
            ids = [chunk.get("id") for chunk in changed_chunks]
            vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)

        vector_store.save_local(str(self.index_dir))

    def load_index(self) -> FAISS:
        return FAISS.load_local(
            str(self.index_dir),
            embeddings=self.embedding_adapter,
            allow_dangerous_deserialization=True,
        )
