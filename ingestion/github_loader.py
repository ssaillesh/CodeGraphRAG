from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from git import Repo


@dataclass
class RepoMetadata:
    repo_url: str
    repo_name: str
    local_path: Path
    default_branch: Optional[str]


class GitHubLoader:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def clone_or_open(self, repo_url: str, branch: Optional[str] = None) -> RepoMetadata:
        repo_name = self._repo_name_from_url(repo_url)
        local_path = self.cache_dir / repo_name

        if local_path.exists() and (local_path / ".git").exists():
            repo = Repo(local_path)
            repo.remotes.origin.fetch()
        else:
            clone_kwargs = {"to_path": str(local_path)}
            if branch:
                clone_kwargs["branch"] = branch
            repo = Repo.clone_from(repo_url, **clone_kwargs)

        if branch:
            repo.git.checkout(branch)
            repo.remotes.origin.pull(branch)

        active_branch = None
        try:
            active_branch = repo.active_branch.name
        except TypeError:
            active_branch = None

        return RepoMetadata(
            repo_url=repo_url,
            repo_name=repo_name,
            local_path=local_path,
            default_branch=active_branch,
        )

    @staticmethod
    def _repo_name_from_url(repo_url: str) -> str:
        parsed = urlparse(repo_url)
        name = parsed.path.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        if not name:
            raise ValueError(f"Unable to infer repository name from URL: {repo_url}")
        return name
