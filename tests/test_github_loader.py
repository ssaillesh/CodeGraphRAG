from pathlib import Path

from git import Repo

from ingestion.github_loader import GitHubLoader


def test_repo_name_parsing() -> None:
    assert GitHubLoader._repo_name_from_url("https://github.com/org/repo.git") == "repo"
    assert GitHubLoader._repo_name_from_url("https://github.com/org/repo") == "repo"


def test_clone_or_open_from_local_origin(tmp_path: Path) -> None:
    origin = tmp_path / "origin_repo"
    origin.mkdir()
    repo = Repo.init(origin)

    file_path = origin / "main.py"
    file_path.write_text("print('hello')\n", encoding="utf-8")
    repo.index.add(["main.py"])
    repo.index.commit("initial")

    loader = GitHubLoader(cache_dir=tmp_path / "cache")
    metadata = loader.clone_or_open(str(origin))

    assert metadata.local_path.exists()
    assert (metadata.local_path / "main.py").exists()
