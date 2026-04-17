from __future__ import annotations

import time
import argparse
from typing import Optional

from git import Git

from workers.celery_worker import run_pipeline_task


class RepoWatcher:
    def __init__(self, poll_interval_seconds: int = 300):
        self.poll_interval_seconds = poll_interval_seconds
        self._latest_seen: dict[str, str] = {}

    def watch(self, repo_url: str, branch: str = "main", publish: bool = True) -> None:
        while True:
            remote_hash = self._get_remote_head(repo_url, branch)
            if remote_hash and self._latest_seen.get(repo_url) != remote_hash:
                self._latest_seen[repo_url] = remote_hash
                run_pipeline_task.delay(repo_url=repo_url, branch=branch, publish=publish)
            time.sleep(self.poll_interval_seconds)

    @staticmethod
    def _get_remote_head(repo_url: str, branch: str) -> Optional[str]:
        try:
            output = Git().ls_remote(repo_url, f"refs/heads/{branch}")
            if not output:
                return None
            return output.split()[0]
        except Exception:
            return None


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

