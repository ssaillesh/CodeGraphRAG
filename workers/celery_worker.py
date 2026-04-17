from __future__ import annotations

from typing import Optional

from celery import Celery

from config import settings
from workers.pipeline import DocumentationPipeline

celery_app = Celery(
    "ai_codebase_doc_system",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


@celery_app.task(name="docs.run_pipeline")
def run_pipeline_task(repo_url: str, branch: Optional[str] = None, publish: bool = False) -> dict:
    pipeline = DocumentationPipeline()
    return pipeline.run_full_pipeline(repo_url=repo_url, branch=branch, publish=publish)
