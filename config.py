from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI Codebase Documentation System"
    environment: str = "development"

    workspace_root: Path = Path("./workspace")
    repo_cache_dir: Path = Path("./workspace/repos")
    index_dir: Path = Path("./workspace/index")
    sqlite_path: Path = Path("./workspace/doc_runs.db")

    chunk_size: int = 1200
    chunk_overlap: int = 150
    max_file_size_bytes: int = 1_000_000
    supported_extensions: List[str] = Field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".go",
            ".rs",
            ".md",
            ".yaml",
            ".yml",
            ".json",
        ]
    )
    exclude_dirs: List[str] = Field(
        default_factory=lambda: [
            ".git",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            "__pycache__",
            ".pytest_cache",
        ]
    )

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model_name: str = "mistralai/Mistral-7B-Instruct-v0.3"
    llm_device_map: str = "auto"

    # NVIDIA Llama for codebase descriptions
    nvidia_api_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_api_key: str = ""
    nvidia_llm_model: str = "meta/llama-3.1-70b-instruct"

    vector_store_type: str = "faiss"

    confluence_base_url: str = ""
    confluence_email: str = ""
    confluence_api_token: str = ""
    confluence_space_key: str = "DOC"
    confluence_root_page_title: str = "AI Generated Codebase Docs"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"


settings = Settings()
