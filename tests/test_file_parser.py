from pathlib import Path

from ingestion.file_parser import FileParser


def test_parse_repository_filters_and_loads(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")
    (repo / "README.md").write_text("# Title\n", encoding="utf-8")
    (repo / "ignored.bin").write_bytes(b"\x00\x01")
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "dep.js").write_text("export const x = 1", encoding="utf-8")

    parser = FileParser(
        supported_extensions=[".py", ".md", ".js"],
        exclude_dirs=["node_modules", ".git"],
        max_file_size_bytes=1024,
    )
    docs = parser.parse_repository(repo)

    rel_paths = {d.relative_path for d in docs}
    assert "app.py" in rel_paths
    assert "README.md" in rel_paths
    assert "node_modules/dep.js" not in rel_paths
    assert "ignored.bin" not in rel_paths
