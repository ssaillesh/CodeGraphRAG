from __future__ import annotations

import sqlite3
import json
from pathlib import Path
from typing import Optional

from ingestion.file_parser import FileDocument


class StateStore:
    def __init__(self, sqlite_path: Path):
        self.sqlite_path = sqlite_path
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_index_state (
                    repo_url TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    chunk_ids TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo_url, relative_path)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS doc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_url TEXT NOT NULL,
                    commit_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get_repo_file_state(self, repo_url: str) -> dict[str, dict]:
        with sqlite3.connect(self.sqlite_path) as conn:
            rows = conn.execute(
                "SELECT relative_path, sha256, chunk_ids FROM file_index_state WHERE repo_url = ?",
                (repo_url,),
            ).fetchall()

        state: dict[str, dict] = {}
        for relative_path, sha256, chunk_ids_raw in rows:
            state[relative_path] = {
                "sha256": sha256,
                "chunk_ids": json.loads(chunk_ids_raw),
            }
        return state

    def compute_incremental_changes(
        self,
        repo_url: str,
        current_files: list[FileDocument],
    ) -> tuple[list[FileDocument], list[str], list[str], list[FileDocument]]:
        previous_state = self.get_repo_file_state(repo_url)
        current_by_path = {f.relative_path: f for f in current_files}

        changed_files: list[FileDocument] = []
        unchanged_files: list[FileDocument] = []
        removed_chunk_ids: list[str] = []

        for relative_path, file_doc in current_by_path.items():
            prev = previous_state.get(relative_path)
            if prev is None or prev["sha256"] != file_doc.sha256:
                changed_files.append(file_doc)
                if prev:
                    removed_chunk_ids.extend(prev["chunk_ids"])
            else:
                unchanged_files.append(file_doc)

        deleted_files = [p for p in previous_state.keys() if p not in current_by_path]
        for relative_path in deleted_files:
            removed_chunk_ids.extend(previous_state[relative_path]["chunk_ids"])

        return changed_files, deleted_files, removed_chunk_ids, unchanged_files

    def upsert_file_index_state(
        self,
        repo_url: str,
        relative_path: str,
        sha256: str,
        chunk_ids: list[str],
    ) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO file_index_state (repo_url, relative_path, sha256, chunk_ids)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(repo_url, relative_path)
                DO UPDATE SET
                    sha256 = excluded.sha256,
                    chunk_ids = excluded.chunk_ids,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (repo_url, relative_path, sha256, json.dumps(chunk_ids)),
            )
            conn.commit()

    def delete_file_index_state(self, repo_url: str, relative_paths: list[str]) -> None:
        if not relative_paths:
            return
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.executemany(
                "DELETE FROM file_index_state WHERE repo_url = ? AND relative_path = ?",
                [(repo_url, path) for path in relative_paths],
            )
            conn.commit()

    def record_run(self, repo_url: str, commit_hash: Optional[str]) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                "INSERT INTO doc_runs (repo_url, commit_hash) VALUES (?, ?)",
                (repo_url, commit_hash),
            )
            conn.commit()
