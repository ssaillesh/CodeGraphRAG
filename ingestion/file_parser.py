from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class FileDocument:
    path: Path
    relative_path: str
    language: str
    content: str
    sha256: str


class FileParser:
    LANGUAGE_BY_EXTENSION = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".md": "markdown",
        ".json": "json",
        ".yml": "yaml",
        ".yaml": "yaml",
    }

    def __init__(
        self,
        supported_extensions: list[str],
        exclude_dirs: list[str],
        max_file_size_bytes: int,
    ):
        self.supported_extensions = set(supported_extensions)
        self.exclude_dirs = set(exclude_dirs)
        self.max_file_size_bytes = max_file_size_bytes

    def parse_repository(self, repo_path: Path) -> list[FileDocument]:
        documents: list[FileDocument] = []
        for file_path in self._iter_candidate_files(repo_path):
            doc = self._parse_file(repo_path, file_path)
            if doc:
                documents.append(doc)
        return documents

    def _iter_candidate_files(self, repo_path: Path) -> Iterable[Path]:
        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.exclude_dirs for part in path.parts):
                continue
            if path.suffix.lower() not in self.supported_extensions:
                continue
            if path.stat().st_size > self.max_file_size_bytes:
                continue
            yield path

    def _parse_file(self, repo_path: Path, file_path: Path) -> Optional[FileDocument]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

        relative_path = str(file_path.relative_to(repo_path))
        language = self.LANGUAGE_BY_EXTENSION.get(file_path.suffix.lower(), "text")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return FileDocument(
            path=file_path,
            relative_path=relative_path,
            language=language,
            content=content,
            sha256=digest,
        )
