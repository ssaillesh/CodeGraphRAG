from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from git import Repo

from compiler.confluence_formatter import ConfluenceFormatter
from config import settings
from ingestion.ast_parser import ASTParser
from ingestion.file_parser import FileDocument, FileParser
from ingestion.github_loader import GitHubLoader
from integrations.confluence_client import ConfluenceClient
from llm.doc_generator import DocumentationGenerator
from rag.embeddings import EmbeddingModel
from rag.retriever import CodeRetriever
from rag.vector_store import VectorStoreManager
from workers.state_store import StateStore


@dataclass
class IngestionResult:
    repo_path: Path
    files: list[FileDocument]
    changed_files: list[FileDocument]
    unchanged_files: list[FileDocument]
    deleted_files: list[str]
    removed_chunk_ids: list[str]
    module_summaries: list[dict]
    commit_hash: Optional[str]


class DocumentationPipeline:
    def __init__(self):
        self.loader = GitHubLoader(settings.repo_cache_dir)
        self.file_parser = FileParser(
            supported_extensions=settings.supported_extensions,
            exclude_dirs=settings.exclude_dirs,
            max_file_size_bytes=settings.max_file_size_bytes,
        )
        self.ast_parser = ASTParser()
        self.embedding_model = EmbeddingModel(settings.embedding_model_name)
        self.vector_store: Optional[VectorStoreManager] = None
        self.doc_generator = DocumentationGenerator(model_loader=None)
        self.confluence_formatter = ConfluenceFormatter()
        self.state_store = StateStore(settings.sqlite_path)

    def ingest_repository(self, repo_url: str, branch: Optional[str] = None) -> IngestionResult:
        metadata = self.loader.clone_or_open(repo_url, branch=branch)
        docs = self.file_parser.parse_repository(metadata.local_path)
        changed_files, deleted_files, removed_chunk_ids, unchanged_files = (
            self.state_store.compute_incremental_changes(repo_url, docs)
        )
        summaries = self._build_module_summaries(docs)
        commit_hash = self._head_commit(metadata.local_path)
        return IngestionResult(
            repo_path=metadata.local_path,
            files=docs,
            changed_files=changed_files,
            unchanged_files=unchanged_files,
            deleted_files=deleted_files,
            removed_chunk_ids=removed_chunk_ids,
            module_summaries=summaries,
            commit_hash=commit_hash,
        )

    def build_index(self, repo_url: str, repo_name: str, ingestion_result: IngestionResult) -> dict:
        index_dir = settings.index_dir / repo_name
        self.vector_store = VectorStoreManager(index_dir, self.embedding_model)

        changed_chunks, chunk_id_map = self._chunk_files(ingestion_result.changed_files)
        self.vector_store.incremental_update(changed_chunks, ingestion_result.removed_chunk_ids)

        for file_doc in ingestion_result.changed_files:
            self.state_store.upsert_file_index_state(
                repo_url=repo_url,
                relative_path=file_doc.relative_path,
                sha256=file_doc.sha256,
                chunk_ids=chunk_id_map.get(file_doc.relative_path, []),
            )

        self.state_store.delete_file_index_state(repo_url, ingestion_result.deleted_files)

        return {
            "changed_files": len(ingestion_result.changed_files),
            "unchanged_files": len(ingestion_result.unchanged_files),
            "deleted_files": len(ingestion_result.deleted_files),
            "changed_chunks": len(changed_chunks),
        }

    def run_full_pipeline(self, repo_url: str, branch: Optional[str] = None, publish: bool = False) -> dict:
        ingestion_result = self.ingest_repository(repo_url, branch=branch)
        index_stats = self.build_index(repo_url, ingestion_result.repo_path.name, ingestion_result)

        if self.vector_store is None or not self.vector_store.has_index():
            evidence = []
        else:
            retriever = CodeRetriever(self.vector_store.load_index())
            evidence = retriever.retrieve("Summarize architecture and modules")

        payload = self.doc_generator.generate(
            repo_name=ingestion_result.repo_path.name,
            module_summaries=ingestion_result.module_summaries,
            retrieval_context=evidence,
            files=ingestion_result.files,
            modules=[m["module"] for m in ingestion_result.module_summaries],
        )

        ready_page = self.confluence_formatter.build_ready_page(
            payload,
            settings.confluence_root_page_title,
        )
        pages = self.confluence_formatter.to_pages(payload, settings.confluence_root_page_title)
        publish_results = []
        if publish:
            client = ConfluenceClient(
                base_url=settings.confluence_base_url,
                email=settings.confluence_email,
                api_token=settings.confluence_api_token,
                space_key=settings.confluence_space_key,
            )
            publish_results = [r.model_dump() for r in client.publish_tree(pages)]

        self.state_store.record_run(repo_url, ingestion_result.commit_hash)

        return {
            "repo_path": str(ingestion_result.repo_path),
            "files_indexed": len(ingestion_result.files),
            "changed_files_indexed": index_stats["changed_files"],
            "unchanged_files_skipped": index_stats["unchanged_files"],
            "deleted_files_removed": index_stats["deleted_files"],
            "changed_chunks_indexed": index_stats["changed_chunks"],
            "modules_detected": len(ingestion_result.module_summaries),
            "pages_generated": len(pages),
            "confluence_page": ready_page.model_dump(),
            "published": publish,
            "publish_results": publish_results,
            "commit_hash": ingestion_result.commit_hash,
        }

    def _chunk_files(self, files: list[FileDocument]) -> tuple[list[dict], dict[str, list[str]]]:
        chunks: list[dict] = []
        chunk_id_map: dict[str, list[str]] = {}
        size = settings.chunk_size
        overlap = settings.chunk_overlap
        step = max(size - overlap, 1)

        for file_doc in files:
            text = file_doc.content
            for start in range(0, len(text), step):
                chunk = text[start : start + size]
                if not chunk.strip():
                    continue
                chunk_id = f"{file_doc.relative_path}:{file_doc.sha256}:{start}"
                chunk_id_map.setdefault(file_doc.relative_path, []).append(chunk_id)
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": {
                            "relative_path": file_doc.relative_path,
                            "language": file_doc.language,
                            "sha256": file_doc.sha256,
                        },
                    }
                )
        return chunks, chunk_id_map

    def _build_module_summaries(self, files: list[FileDocument]) -> list[dict]:
        summaries = []
        for file_doc in files:
            symbols = self.ast_parser.extract_symbols(file_doc)
            summaries.append(
                {
                    "module": file_doc.relative_path,
                    "purpose": f"Implements logic in {file_doc.relative_path}",
                    "functions": [s.name for s in symbols if "function" in s.symbol_type],
                    "dependencies": self._extract_dependencies(file_doc),
                }
            )
        return summaries

    @staticmethod
    def _extract_dependencies(file_doc: FileDocument) -> list[str]:
        deps: list[str] = []
        for line in file_doc.content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                deps.append(stripped)
        return deps[:50]

    @staticmethod
    def _head_commit(repo_path: Path) -> Optional[str]:
        try:
            repo = Repo(repo_path)
            return repo.head.commit.hexsha
        except Exception:
            return None
