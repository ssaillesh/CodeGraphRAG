import json
from typing import Any

from compiler.doc_schema import DocumentationPayload, ModuleDoc
from integrations.llama_describer import get_describer
from llm.prompt_templates import documentation_prompt
from ingestion.file_parser import FileDocument


class DocumentationGenerator:
    def __init__(self, model_loader=None):
        self.model_loader = model_loader

    def generate(
        self,
        repo_name: str,
        module_summaries: list[dict[str, Any]],
        retrieval_context: list[dict[str, Any]],
        files: list = None,
        modules: list[str] = None,
    ) -> DocumentationPayload:
        files = files or []
        modules = modules or []

        if self.model_loader is not None:
            prompt = documentation_prompt(repo_name, module_summaries, retrieval_context)
            response = self.model_loader.generate(prompt)
            return self._parse_response(repo_name, response, module_summaries, files, modules)

        describer = get_describer()
        if describer and files:
            readme_json = describer.generate_readme_documentation(
                repo_name=repo_name,
                files=files,
                module_summaries=module_summaries,
                evidence=retrieval_context,
            )
            if readme_json:
                return self._parse_payload(repo_name, readme_json, module_summaries, files, modules)

        return self._deterministic_fallback(repo_name, module_summaries, files, modules)

    def _deterministic_fallback(
        self,
        repo_name: str,
        module_summaries: list[dict[str, Any]],
        files: list = None,
        modules: list[str] = None,
    ) -> DocumentationPayload:
        files = files or []
        modules = modules or []
        module_docs = [
            ModuleDoc(
                module=m.get("module", "unknown"),
                purpose=m.get("purpose", "No purpose extracted."),
                functions=m.get("functions", []),
                dependencies=m.get("dependencies", []),
            )
            for m in module_summaries
        ]

        title = self._title_from_repo_name(repo_name)
        subtitle = f"Enterprise system documentation for {repo_name}."
        system_design_overview = (
            "This repository is organized as a layered application where the entry point coordinates core application logic, supporting helpers, and documentation or orchestration code. The design is intentionally modular so that each section of the workflow can evolve without forcing changes across the whole system."
        )
        architecture_diagram = (
            "User / Operator -> Entry Point -> Core Application Layer -> Supporting Utilities -> Outputs / Artifacts"
        )
        requirements_functional = (
            "The system should generate a polished documentation pack from repository evidence, summarize the project structure, and present the results in a Confluence-friendly format that can be published directly as an internal engineering page."
        )
        requirements_nonfunctional = (
            "The documentation pipeline should remain deterministic, resilient to incomplete repositories, and able to produce readable output even when README content is sparse or missing. The result should stay concise enough for internal review while remaining complete enough to explain purpose, structure, and usage."
        )
        requirements_dependencies = [
            "Python runtime",
            "Project source files or repository checkout",
            "Confluence publishing credentials when publishing is enabled",
        ]
        usage_overview = (
            "Users run the documentation pipeline against a repository URL or local checkout, then review the generated Confluence pages for the system design summary, requirements, and usage guidance. The top-level page is meant to read like a polished internal document rather than a tool log or code dump."
        )
        execution_lifecycle = [
            "Identify repository contents and load source files.",
            "Extract structural evidence and module summaries.",
            "Generate the enterprise documentation pack.",
            "Render the result into Confluence pages.",
            "Optionally publish the pages to the configured space.",
        ]
        summary = (
            "This documentation pack explains what the repository does, how it is structured, what it requires, and how to use it in practice. It is designed for internal engineering audiences who want a fast but credible understanding of the system."
        )
        project_structure = self._build_project_structure(files)
        tech_stack = self._infer_tech_stack(files)
        api_reference = self._summarize_api_reference(files)
        quick_start = [
            "Clone the repository.",
            "Create and activate a virtual environment.",
            "Install the dependencies listed in the project manifest.",
            "Start the application or docs pipeline using the repository entry point.",
        ]
        usage_guide = [
            "Open the UI or run the API endpoints from the README instructions.",
            "Configure environment variables before running the application.",
            "Use the main routes or scripts to exercise the core workflow.",
        ]
        validation_testing = [
            "Run the available test suite.",
            "Validate key flows against sample inputs.",
            "Check the generated documentation against the repository source.",
        ]

        overview = f"Technical documentation for repository {repo_name}."
        architecture = "The repository is organized into application logic, supporting utilities, and documentation or orchestration layers."
        mathematical_formulation = "Not applicable."
        use_case = "This repository appears to support developers or users working with the project's core application workflow."
        key_features = "Core application logic, supporting utilities, and project documentation generation."

        return DocumentationPayload(
            repository=repo_name,
            title=title,
            subtitle=subtitle,
            table_of_contents=self._default_toc(),
            system_design_overview=system_design_overview,
            architecture_diagram=architecture_diagram,
            requirements_functional=requirements_functional,
            requirements_nonfunctional=requirements_nonfunctional,
            requirements_dependencies=requirements_dependencies,
            usage_overview=usage_overview,
            execution_lifecycle=execution_lifecycle,
            summary=summary,
            overview=overview,
            architecture=architecture,
            mathematical_formulation=mathematical_formulation,
            features=[
                "Human-readable project documentation",
                "Repository-aware module summaries",
                "README-style section rendering",
            ],
            tech_stack=tech_stack,
            project_structure=project_structure,
            quick_start=quick_start,
            usage_guide=usage_guide,
            api_reference=api_reference,
            validation_testing=validation_testing,
            performance_notes="Documentation generation is optimized for incremental repository indexing and compact payloads.",
            roadmap_ideas=[
                "Add deeper repository-specific examples.",
                "Infer more exact command-line usage from project manifests.",
                "Generate repo-specific diagrams when enough evidence is available.",
            ],
            license="Unknown",
            use_case=use_case,
            key_features=key_features,
            modules=module_docs,
            api_documentation="API documentation is generated from discovered route and function signatures.",
            setup_guide="Install dependencies, configure .env, and run the application entry point for this repository.",
            developer_notes="Review generated docs after major refactors and refine the README structure with repository-specific facts.",
        )

    def _parse_response(
        self,
        repo_name: str,
        response: str,
        module_summaries: list[dict[str, Any]],
        files: list,
        modules: list[str],
    ) -> DocumentationPayload:
        try:
            data = json.loads(response)
            return self._parse_payload(repo_name, data, module_summaries, files, modules)
        except Exception:
            return self._deterministic_fallback(repo_name, module_summaries)

    def _parse_payload(
        self,
        repo_name: str,
        data: dict,
        module_summaries: list[dict[str, Any]],
        files: list,
        modules: list[str],
    ) -> DocumentationPayload:
        module_docs = [
            ModuleDoc(
                module=m.get("module", "unknown"),
                purpose=m.get("purpose", m.get("role_in_system", "No purpose extracted.")),
                functions=m.get("functions", []),
                dependencies=m.get("dependencies", []),
            )
            for m in module_summaries
        ]

        defaults = self._deterministic_fallback(repo_name, module_summaries, files, modules)
        return DocumentationPayload(
            repository=repo_name,
            title=self._as_text(data.get("title", defaults.title), defaults.title),
            subtitle=self._as_text(data.get("subtitle", defaults.subtitle), defaults.subtitle),
            table_of_contents=self._as_list(data.get("table_of_contents", defaults.table_of_contents), defaults.table_of_contents),
            system_design_overview=self._as_text(data.get("system_design_overview", defaults.system_design_overview), defaults.system_design_overview),
            architecture_diagram=self._as_text(data.get("architecture_diagram", defaults.architecture_diagram), defaults.architecture_diagram),
            requirements_functional=self._as_text(data.get("requirements_functional", defaults.requirements_functional), defaults.requirements_functional),
            requirements_nonfunctional=self._as_text(data.get("requirements_nonfunctional", defaults.requirements_nonfunctional), defaults.requirements_nonfunctional),
            requirements_dependencies=self._as_list(data.get("requirements_dependencies", defaults.requirements_dependencies), defaults.requirements_dependencies),
            usage_overview=self._as_text(data.get("usage_overview", defaults.usage_overview), defaults.usage_overview),
            execution_lifecycle=self._as_list(data.get("execution_lifecycle", defaults.execution_lifecycle), defaults.execution_lifecycle),
            summary=self._as_text(data.get("summary", defaults.summary), defaults.summary),
            overview=self._as_text(data.get("overview", defaults.overview), defaults.overview),
            architecture=self._as_text(data.get("architecture", defaults.architecture), defaults.architecture),
            mathematical_formulation=self._as_text(data.get("mathematical_formulation", defaults.mathematical_formulation), defaults.mathematical_formulation),
            features=self._as_list(data.get("features", defaults.features), defaults.features),
            tech_stack=self._as_list(data.get("tech_stack", defaults.tech_stack), defaults.tech_stack),
            project_structure=self._as_text(data.get("project_structure", defaults.project_structure), defaults.project_structure),
            quick_start=self._as_list(data.get("quick_start", defaults.quick_start), defaults.quick_start),
            usage_guide=self._as_list(data.get("usage_guide", defaults.usage_guide), defaults.usage_guide),
            api_reference=self._as_list(data.get("api_reference", defaults.api_reference), defaults.api_reference),
            validation_testing=self._as_list(data.get("validation_testing", defaults.validation_testing), defaults.validation_testing),
            performance_notes=self._as_text(data.get("performance_notes", defaults.performance_notes), defaults.performance_notes),
            roadmap_ideas=self._as_list(data.get("roadmap_ideas", defaults.roadmap_ideas), defaults.roadmap_ideas),
            license=self._as_text(data.get("license", defaults.license), defaults.license),
            use_case=self._as_text(data.get("use_case", defaults.use_case), defaults.use_case),
            key_features=self._as_text(data.get("key_features", defaults.key_features), defaults.key_features),
            modules=module_docs,
            api_documentation=self._as_text(data.get("api_documentation", defaults.api_documentation), defaults.api_documentation),
            setup_guide=self._as_text(data.get("setup_guide", defaults.setup_guide), defaults.setup_guide),
            developer_notes=self._as_text(data.get("developer_notes", defaults.developer_notes), defaults.developer_notes),
        )

    @staticmethod
    def _title_from_repo_name(repo_name: str) -> str:
        clean = repo_name.replace("_", " ").replace("-", " ").strip()
        return clean.title() if clean else "Documentation"

    @staticmethod
    def _default_toc() -> list[str]:
        return [
            "System Design Overview",
            "Requirements",
            "How to Use",
            "System Execution Lifecycle",
            "Summary",
        ]

    @staticmethod
    def _build_project_structure(files: list) -> str:
        if not files:
            return "Unknown"

        top_level = sorted({f.relative_path.split("/")[0] for f in files[:40]})
        return "Repository layout inferred from files: " + ", ".join(top_level)

    @staticmethod
    def _infer_tech_stack(files: list) -> list[str]:
        if not files:
            return ["Unknown"]

        languages = sorted({f.language for f in files if getattr(f, "language", "")})
        stack = languages[:8]
        if any(f.relative_path.endswith("requirements.txt") for f in files):
            stack.append("Python packaging / requirements.txt")
        if any(f.relative_path.endswith("package.json") for f in files):
            stack.append("Node.js / package.json")
        return stack or ["Unknown"]

    @staticmethod
    def _summarize_api_reference(files: list) -> list[str]:
        api_files = [f.relative_path for f in files if any(token in f.relative_path.lower() for token in ("api", "routes", "server", "app", "main"))]
        return api_files[:10] or ["Unknown"]

    @staticmethod
    def _as_text(value: Any, default: str = "") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            joined = "\n".join(str(item) for item in value if item is not None)
            return joined or default
        return str(value)

    @staticmethod
    def _as_list(value: Any, default: list[str] | None = None) -> list[str]:
        default = default or []
        if value is None:
            return default
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, str):
            lines = [line.strip("-• \t") for line in value.splitlines() if line.strip()]
            return lines or [value]
        return [str(value)]
