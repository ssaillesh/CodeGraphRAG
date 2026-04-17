"""
Llama-based codebase description generator using NVIDIA's API.
Generates human-readable summaries of what a codebase does, its purpose, and key functionality.
"""
from __future__ import annotations

import json
from importlib import import_module
from typing import Optional

from config import settings
from ingestion.file_parser import FileDocument


class CodebaseDescriber:
    """Generate human-readable descriptions using NVIDIA's Llama 3.1-70B model."""

    def __init__(self):
        """Initialize NVIDIA Llama client."""
        try:
            openai_module = import_module("openai")
            openai_client = openai_module.OpenAI
        except ModuleNotFoundError as exc:
            raise ValueError(
                "The openai package is not installed. Install requirements to enable NVIDIA Llama support."
            ) from exc

        if not settings.nvidia_api_key:
            raise ValueError(
                "NVIDIA_API_KEY not configured. "
                "Get a free key at https://build.nvidia.com/, then set it in .env"
            )

        self.client = openai_client(
            base_url=settings.nvidia_api_base_url,
            api_key=settings.nvidia_api_key,
        )
        self.model = settings.nvidia_llm_model

    def generate_overview(
        self,
        repo_name: str,
        files: list[FileDocument],
        modules: list[str],
        max_tokens: int = 300,
    ) -> str:
        """
        Generate a high-level overview of what the codebase does.

        Args:
            repo_name: Name of the repository
            files: List of parsed files
            modules: List of detected modules
            max_tokens: Maximum tokens for response

        Returns:
            Human-readable overview of the codebase
        """
        file_list = "\n".join(
            [f"- {f.relative_path}: {self._summarize_file(f)}" for f in files[:20]]
        )
        modules_str = ", ".join(modules[:10]) if modules else "None detected"

        prompt = f"""Analyze this codebase and provide a concise, human-readable overview of what it does, its purpose, and main functionality.

Repository: {repo_name}
Files analyzed: {len(files)}
Modules: {modules_str}

Top files:
{file_list}

Provide a 2-3 sentence overview that would help a developer quickly understand the codebase's purpose and main use case."""

        return self._stream_completion(prompt, max_tokens)

    def generate_architecture_summary(
        self,
        files: list[FileDocument],
        modules: list[str],
        max_tokens: int = 400,
    ) -> str:
        """
        Generate a description of the codebase architecture and components.

        Args:
            files: List of parsed files
            modules: List of detected modules
            max_tokens: Maximum tokens for response

        Returns:
            Human-readable architecture summary
        """
        module_details = "\n".join([f"- {m}" for m in modules[:15]])

        prompt = f"""Based on these detected modules and files, describe the architecture and key components of this codebase.

Modules detected:
{module_details}

File count: {len(files)}
File types: {', '.join(set(f.language for f in files[:10]))}

Provide a clear, technical description of how the system is organized and what the main components do."""

        return self._stream_completion(prompt, max_tokens)

    def generate_use_case(
        self,
        repo_name: str,
        files: list[FileDocument],
        max_tokens: int = 250,
    ) -> str:
        """
        Generate a description of the codebase's intended use and target users.

        Args:
            repo_name: Name of the repository
            files: List of parsed files
            max_tokens: Maximum tokens for response

        Returns:
            Human-readable use case description
        """
        file_summary = "\n".join(
            [f"- {f.relative_path}: {self._summarize_file(f)}" for f in files[:15]]
        )

        prompt = f"""Based on this codebase, who would use it and what problem does it solve?

Repository: {repo_name}
Files:
{file_summary}

Provide a concise description of the intended use case, target users, and problems it solves."""

        return self._stream_completion(prompt, max_tokens)

    def generate_key_features(
        self,
        files: list[FileDocument],
        max_tokens: int = 350,
    ) -> str:
        """
        Generate a list of key features and capabilities.

        Args:
            files: List of parsed files
            max_tokens: Maximum tokens for response

        Returns:
            List of key features as formatted string
        """
        file_summary = "\n".join(
            [f"- {f.relative_path}: {self._summarize_file(f)}" for f in files[:20]]
        )

        prompt = f"""List the key features and capabilities of this codebase in a structured, easy-to-read format.

Files:
{file_summary}

Provide 5-8 main features as a simple list. Format as:
- Feature name: brief description
- Another feature: brief description
etc."""

        return self._stream_completion(prompt, max_tokens)

    def generate_readme_documentation(
        self,
        repo_name: str,
        files: list[FileDocument],
        module_summaries: list[dict],
        evidence: list[dict],
        max_tokens: int = 2200,
    ) -> dict:
        file_context = "\n".join(
            [f"- {f.relative_path} ({f.language}): {self._summarize_file(f)}" for f in files[:30]]
        )
        module_context = json.dumps(module_summaries[:30], indent=2)
        evidence_context = json.dumps(evidence[:20], indent=2)

        prompt = f"""Write a polished README-style project document for this repository.

Repository: {repo_name}

Use this structure and return STRICT JSON only:
{{
  "title": "",
  "subtitle": "",
  "table_of_contents": [],
  "overview": "",
  "architecture": "",
  "mathematical_formulation": "",
  "features": [],
  "tech_stack": [],
  "project_structure": "",
  "quick_start": [],
  "usage_guide": [],
  "api_reference": [],
  "validation_testing": [],
  "performance_notes": "",
  "roadmap_ideas": [],
  "license": "",
  "use_case": "",
  "key_features": "",
  "api_documentation": "",
  "setup_guide": "",
  "developer_notes": ""
}}

Guidance for the content:
- Use a README voice: concise, practical, human-readable.
- Mirror the example sections: Overview, Features, Tech Stack, Project Structure, Quick Start, Usage Guide, API Reference, Validation & Testing, Performance Notes, Roadmap Ideas, License.
- If the repository is not mathematical or ML-focused, set "mathematical_formulation" to "Not applicable.".
- If there is no obvious license, set license to "Unknown".
- Derive project structure from the codebase layout and filenames.
- Prefer evidence from the repository contents over inference.

Repository files:
{file_context}

Module summaries:
{module_context}

Evidence:
{evidence_context}
"""

        response = self._stream_completion(prompt, max_tokens)
        try:
            return json.loads(response)
        except Exception:
            return {}

    def _stream_completion(self, prompt: str, max_tokens: int) -> str:
        """
        Stream completion from Llama model and collect response.

        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum tokens for response

        Returns:
            Complete response text
        """
        full_response = ""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                top_p=0.7,
                max_tokens=max_tokens,
                stream=True,
            )

            for chunk in completion:
                if (
                    chunk.choices
                    and chunk.choices[0].delta.content is not None
                ):
                    full_response += chunk.choices[0].delta.content

        except Exception as e:
            # Graceful fallback if API fails
            return f"(Unable to generate description: {str(e)})"

        return full_response.strip()

    @staticmethod
    def _summarize_file(file_doc: FileDocument, max_lines: int = 3, max_chars: int = 180) -> str:
        lines = [line.strip() for line in file_doc.content.splitlines() if line.strip()]
        if not lines:
            return "No readable content extracted."
        snippet = " | ".join(lines[:max_lines])
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars].rstrip() + "..."
        return snippet


# Singleton instance
_describer: Optional[CodebaseDescriber] = None


def get_describer() -> Optional[CodebaseDescriber]:
    """Get or create the describer instance. Returns None if API key not configured."""
    global _describer
    if _describer is None:
        try:
            _describer = CodebaseDescriber()
        except ValueError:
            # API key not configured, return None
            return None
    return _describer
