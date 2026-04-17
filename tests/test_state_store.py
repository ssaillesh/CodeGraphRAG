from pathlib import Path

from ingestion.file_parser import FileDocument
from workers.state_store import StateStore


def _doc(path: Path, relative_path: str, content: str, sha256: str) -> FileDocument:
    return FileDocument(
        path=path,
        relative_path=relative_path,
        language="python",
        content=content,
        sha256=sha256,
    )


def test_compute_incremental_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "state.db"
    store = StateStore(db_path)
    repo_url = "https://github.com/org/repo.git"

    store.upsert_file_index_state(repo_url, "a.py", "sha-old-a", ["a-chunk-1", "a-chunk-2"])
    store.upsert_file_index_state(repo_url, "b.py", "sha-b", ["b-chunk-1"])

    current_files = [
        _doc(tmp_path / "a.py", "a.py", "print('new')", "sha-new-a"),
        _doc(tmp_path / "c.py", "c.py", "print('new file')", "sha-c"),
    ]

    changed, deleted, removed_chunk_ids, unchanged = store.compute_incremental_changes(
        repo_url, current_files
    )

    changed_paths = {f.relative_path for f in changed}
    unchanged_paths = {f.relative_path for f in unchanged}

    assert changed_paths == {"a.py", "c.py"}
    assert unchanged_paths == set()
    assert deleted == ["b.py"]
    assert set(removed_chunk_ids) == {"a-chunk-1", "a-chunk-2", "b-chunk-1"}
