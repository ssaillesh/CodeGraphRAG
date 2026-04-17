class CodeRetriever:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 6) -> list[dict]:
        docs = self.vector_store.similarity_search(query, k=top_k)
        return [{"text": d.page_content, "metadata": d.metadata} for d in docs]
