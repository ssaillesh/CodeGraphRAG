from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from config import settings
from compiler.doc_schema import ConfluencePage, ConfluencePublishResult
from integrations.confluence_client import ConfluenceClient
from workers.pipeline import DocumentationPipeline

router = APIRouter(prefix="/api", tags=["documentation"])
pipeline = DocumentationPipeline()


def _home_page_html() -> str:
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Codebase Documentation System</title>
    <style>
        :root {
            color-scheme: dark;
            --bg: #07111f;
            --bg2: #0d1b2a;
            --card: rgba(10, 18, 34, 0.72);
            --card-border: rgba(148, 163, 184, 0.18);
            --text: #e2e8f0;
            --muted: #94a3b8;
            --accent: #22c55e;
            --accent-2: #38bdf8;
            --warn: #f59e0b;
            --shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
        }

        * { box-sizing: border-box; }
        body {
            margin: 0;
            min-height: 100vh;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--text);
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.20), transparent 30%),
                radial-gradient(circle at top right, rgba(34, 197, 94, 0.18), transparent 26%),
                linear-gradient(135deg, var(--bg), var(--bg2));
        }

        .shell {
            max-width: 1320px;
            margin: 0 auto;
            padding: 32px;
        }

        .hero {
            display: grid;
            grid-template-columns: 1.4fr 0.9fr;
            gap: 24px;
            align-items: stretch;
            margin-bottom: 24px;
        }

        .panel {
            background: var(--card);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(18px);
        }

        .brand {
            padding: 28px;
            position: relative;
            overflow: hidden;
        }

        .brand::after {
            content: "";
            position: absolute;
            inset: auto -40px -60px auto;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(34, 197, 94, 0.18), transparent 70%);
            pointer-events: none;
        }

        .eyebrow {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            padding: 7px 12px;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.12);
            color: var(--muted);
            font-size: 12px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        h1 {
            margin: 18px 0 14px;
            font-size: clamp(38px, 5vw, 70px);
            line-height: 0.95;
            letter-spacing: -0.06em;
        }

        .lede {
            max-width: 780px;
            font-size: 16px;
            line-height: 1.7;
            color: #cbd5e1;
            margin: 0;
        }

        .stats {
            display: grid;
            gap: 16px;
            padding: 24px;
        }

        .stat {
            border-radius: 18px;
            padding: 18px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.14);
        }

        .stat .label {
            display: block;
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 8px;
        }

        .stat .value {
            font-size: 18px;
            font-weight: 700;
        }

        .workspace {
            display: grid;
            grid-template-columns: 0.9fr 1.1fr;
            gap: 24px;
            align-items: start;
        }

        .form-card, .results-card {
            padding: 24px;
        }

        .section-title {
            margin: 0 0 14px;
            font-size: 20px;
            letter-spacing: -0.03em;
        }

        .section-subtitle {
            margin: 0 0 20px;
            color: var(--muted);
            line-height: 1.6;
            font-size: 14px;
        }

        .field {
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 13px;
            color: #cbd5e1;
        }

        input[type="text"], input[type="url"] {
            width: 100%;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(15, 23, 42, 0.88);
            color: var(--text);
            border-radius: 14px;
            padding: 14px 16px;
            font-size: 15px;
            outline: none;
        }

        input:focus {
            border-color: rgba(56, 189, 248, 0.6);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.16);
        }

        .inline-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }

        .check-row {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #cbd5e1;
            margin: 6px 0 18px;
            font-size: 14px;
        }

        .actions {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 20px;
        }

        button {
            border: none;
            border-radius: 14px;
            padding: 14px 18px;
            color: #08111f;
            font-weight: 800;
            cursor: pointer;
            transition: transform 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease;
        }

        button:hover { transform: translateY(-1px); }

        .primary {
            background: linear-gradient(135deg, var(--accent), #86efac);
            box-shadow: 0 10px 24px rgba(34, 197, 94, 0.22);
        }

        .secondary {
            background: linear-gradient(135deg, #7dd3fc, var(--accent-2));
            box-shadow: 0 10px 24px rgba(56, 189, 248, 0.22);
        }

        .ghost {
            color: var(--text);
            background: rgba(148, 163, 184, 0.12);
            border: 1px solid rgba(148, 163, 184, 0.18);
        }

        .result {
            background: rgba(2, 6, 23, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            min-height: 360px;
            padding: 18px;
            overflow: auto;
        }

        pre {
            margin: 0;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            color: #dbeafe;
        }

        .status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.16);
            color: #cbd5e1;
            font-size: 13px;
            margin-bottom: 14px;
        }

        .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--warn);
            box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.12);
        }

        .dot.ok {
            background: var(--accent);
            box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.12);
        }

        .footer-note {
            margin-top: 14px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.6;
        }

        @media (max-width: 980px) {
            .hero, .workspace { grid-template-columns: 1fr; }
            .shell { padding: 18px; }
            h1 { font-size: clamp(34px, 10vw, 54px); }
        }
    </style>
</head>
<body>
    <div class="shell">
        <div class="hero">
            <section class="panel brand">
                <span class="eyebrow">Local AI documentation engineer</span>
                <h1>Turn a codebase into living Confluence docs.</h1>
                <p class="lede">
                    Clone or ingest a repository, index changed files only, generate structured documentation, and publish it into a Confluence space. This interface sits on top of the existing FastAPI + Celery pipeline and keeps everything local except the Confluence API.
                </p>
            </section>
            <aside class="panel stats">
                <div class="stat">
                    <span class="label">Pipeline</span>
                    <div class="value">Ingest → index → generate → publish</div>
                </div>
                <div class="stat">
                    <span class="label">Indexing</span>
                    <div class="value">Incremental updates for large repos</div>
                </div>
                <div class="stat">
                    <span class="label">Output</span>
                    <div class="value">Hierarchical Confluence pages</div>
                </div>
            </aside>
        </div>

        <div class="workspace">
            <section class="panel form-card">
                <h2 class="section-title">Run the documentation workflow</h2>
                <p class="section-subtitle">Submit a repository URL, choose a branch, and generate a single ready-to-publish Confluence page in storage format directly in the browser.</p>

                <div id="status" class="status"><span class="dot" id="status-dot"></span><span id="status-text">Checking API health...</span></div>

                <div class="field">
                    <label for="repo-url">Repository URL</label>
                    <input id="repo-url" type="url" value="/Users/saillesh/Desktop/Documentation AI/demo-sample-repo" placeholder="https://github.com/org/repo.git" />
                </div>

                <div class="inline-row">
                    <div class="field">
                        <label for="branch">Branch</label>
                        <input id="branch" type="text" value="main" placeholder="main" />
                    </div>
                    <div class="field">
                        <label for="publish">Publish</label>
                        <div class="check-row">
                            <input id="publish" type="checkbox" />
                            <span>Publish to Confluence</span>
                        </div>
                    </div>
                </div>

                <div class="actions">
                    <button class="ghost" onclick="runIngest()">Ingest only</button>
                    <button class="primary" onclick="runGenerate()">Generate Confluence page</button>
                    <button class="secondary" onclick="checkHealth()">Check health</button>
                </div>

                <div class="footer-note">
                    Tip: keep the demo repo path or swap in a GitHub URL. For local demo runs, the watcher and Celery worker are already configured in solo mode on this machine.
                </div>
            </section>

            <section class="panel results-card">
                <h2 class="section-title">Live output</h2>
                <p class="section-subtitle">Results from API calls will appear here as formatted JSON.</p>
                <div class="result"><pre id="output">Ready. Run ingest or generate to see results.</pre></div>
            </section>
        </div>
    </div>

    <script>
        const output = document.getElementById('output');
        const statusText = document.getElementById('status-text');
        const statusDot = document.getElementById('status-dot');

        function setOutput(data) {
            output.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
        }

        function setStatus(text, ok) {
            statusText.textContent = text;
            statusDot.classList.toggle('ok', !!ok);
        }

        async function checkHealth() {
            setStatus('Checking API health...', false);
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                setStatus('API is healthy', true);
                setOutput({ health: data, timestamp: new Date().toISOString() });
            } catch (error) {
                setStatus('API health check failed', false);
                setOutput({ error: String(error) });
            }
        }

        async function runIngest() {
            const repoUrl = document.getElementById('repo-url').value.trim();
            const branch = document.getElementById('branch').value.trim() || null;
            setStatus('Running ingest...', false);
            setOutput('Submitting ingest request...');
            try {
                const response = await fetch('/api/ingest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: repoUrl, branch })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Ingest failed');
                setStatus('Ingest complete', true);
                setOutput(data);
            } catch (error) {
                setStatus('Ingest failed', false);
                setOutput({ error: String(error) });
            }
        }

        async function runGenerate() {
            const repoUrl = document.getElementById('repo-url').value.trim();
            const branch = document.getElementById('branch').value.trim() || null;
            const publish = document.getElementById('publish').checked;
            setStatus(publish ? 'Generating and publishing Confluence page...' : 'Generating ready Confluence page...', false);
            setOutput('Submitting ready-page request...');
            try {
                const response = await fetch('/api/confluence-page', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ repo_url: repoUrl, branch, publish })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Page generation failed');
                setStatus(publish ? 'Page published to Confluence' : 'Ready-to-publish page generated', true);
                setOutput(data);
            } catch (error) {
                setStatus('Page generation failed', false);
                setOutput({ error: String(error) });
            }
        }

        checkHealth();
    </script>
</body>
</html>
        """


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
