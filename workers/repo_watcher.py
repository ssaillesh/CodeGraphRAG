from __future__ import annotations
#
import argparse
from pathlib import Path
import time
from typing import Optional

from git import Git, Repo

from workers.celery_worker import run_pipeline_task


class RepoWatcher:
    def __init__(self, poll_interval_seconds: int = 300):
        self.poll_interval_seconds = poll_interval_seconds
        self._latest_seen: dict[str, str] = {}

    def watch(self, repo_url: str, branch: str = "main", publish: bool = True) -> None:
        source_kind = "local" if self._is_local_repo(repo_url) else "remote"
        print(
            f"[repo_watcher] Watching {source_kind} repo '{repo_url}' on branch '{branch}' "
            f"every {self.poll_interval_seconds}s (publish={publish})"
        )

        while True:
            head_hash = self._get_head(repo_url, branch)
            if head_hash and self._latest_seen.get(repo_url) != head_hash:
                previous = self._latest_seen.get(repo_url)
                self._latest_seen[repo_url] = head_hash
                if previous:
                    print(f"[repo_watcher] Change detected: {previous[:7]} -> {head_hash[:7]}")
                else:
                    print(f"[repo_watcher] Initial head detected: {head_hash[:7]}")
                self._enqueue_pipeline(repo_url=repo_url, branch=branch, publish=publish)
                print("[repo_watcher] Pipeline task queued")
            elif head_hash is None:
                print(
                    f"[repo_watcher] Unable to resolve head for '{repo_url}' branch '{branch}'. "
                    "Will retry."
                )

            time.sleep(self.poll_interval_seconds)

    @staticmethod
    def _is_local_repo(repo_url: str) -> bool:
        return Path(repo_url).exists()

    @classmethod
    def _get_head(cls, repo_url: str, branch: str) -> Optional[str]:
        if cls._is_local_repo(repo_url):
            return cls._get_local_head(repo_url, branch)
        return cls._get_remote_head(repo_url, branch)

    @staticmethod
    def _get_remote_head(repo_url: str, branch: str) -> Optional[str]:
        try:
            output = Git().ls_remote(repo_url, f"refs/heads/{branch}")
            if not output:
                return None
            return output.split()[0]
        except Exception:
            return None

    @staticmethod
    def _get_local_head(repo_url: str, branch: str) -> Optional[str]:
        try:
            repo = Repo(repo_url)
            if branch in repo.heads:
                return repo.heads[branch].commit.hexsha

            # Fall back to current HEAD for detached or non-standard branch naming.
            return repo.head.commit.hexsha
        except Exception:
            return None

    @staticmethod
    def _enqueue_pipeline(repo_url: str, branch: str, publish: bool) -> None:
        delay_fn = getattr(run_pipeline_task, "delay", None)
        if callable(delay_fn):
            delay_fn(repo_url=repo_url, branch=branch, publish=publish)
            return

        # Fallback for direct execution contexts where Celery task wrappers are unavailable.
        run_pipeline_task(repo_url=repo_url, branch=branch, publish=publish)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Poll a Git repository and trigger doc updates.")
    parser.add_argument("--repo-url", required=True, help="Git repository URL to watch")
    parser.add_argument("--branch", default="main", help="Branch to watch")
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Do not publish to Confluence when updates are detected",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    watcher = RepoWatcher(poll_interval_seconds=args.interval)
    watcher.watch(repo_url=args.repo_url, branch=args.branch, publish=not args.no_publish)

