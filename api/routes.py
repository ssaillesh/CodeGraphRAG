from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from compiler.doc_schema import ConfluencePage, ConfluencePublishResult
from integrations.confluence_client import ConfluenceClient
from workers.pipeline import DocumentationPipeline

router = APIRouter(prefix="/api", tags=["documentation"])
pipeline = DocumentationPipeline()
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_template_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _home_page_html() -> str:
    template = _template_env.get_template("home.html")
    return template.render(default_repo_url=settings.repo_cache_dir / "demo-sample-repo")


class IngestRequest(BaseModel):
    repo_url: str = Field(..., description="Git repository URL")
    branch: Optional[str] = Field(default=None, description="Optional branch name")


class PublishOptions(BaseModel):
    publish: bool = Field(default=False)


class GenerateRequest(IngestRequest, PublishOptions):
    pass


class ConfluencePageResponse(BaseModel):
    title: str
    body_storage: str
    parent_title: Optional[str] = None
    labels: list[str] = Field(default_factory=list)


class ReadyPageResponse(BaseModel):
    confluence_page: ConfluencePageResponse
    publish_result: Optional[ConfluencePublishResult] = None


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(_home_page_html())


@router.post("/ingest")
def ingest_repo(request: IngestRequest) -> dict:
    try:
        result = pipeline.ingest_repository(request.repo_url, branch=request.branch)
        return {
            "repo_path": str(result.repo_path),
            "file_count": len(result.files),
            "module_count": len(result.module_summaries),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate")
def generate_docs(request: GenerateRequest) -> dict:
    try:
        result = pipeline.run_full_pipeline(
            repo_url=request.repo_url,
            branch=request.branch,
            publish=request.publish,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/confluence-page", response_model=ReadyPageResponse)
def generate_confluence_page(request: GenerateRequest) -> ReadyPageResponse:
    try:
        result = pipeline.run_full_pipeline(
            repo_url=request.repo_url,
            branch=request.branch,
            publish=False,
        )
        ready_page = ConfluencePageResponse(**result["confluence_page"])

        publish_result = None
        if request.publish:
            client = ConfluenceClient(
                base_url=settings.confluence_base_url,
                email=settings.confluence_email,
                api_token=settings.confluence_api_token,
                space_key=settings.confluence_space_key,
            )
            publish_result = client.upsert_page(ConfluencePage(**ready_page.model_dump()))

        return ReadyPageResponse(
            confluence_page=ready_page,
            publish_result=publish_result,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
