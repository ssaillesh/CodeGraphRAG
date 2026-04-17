import html

from compiler.doc_schema import ConfluencePage, DocumentationPayload


class ConfluenceFormatter:
    MAX_READY_PAGE_CHARS = 180_000
    MAX_MODULES_IN_READY_PAGE = 80

    @staticmethod
    def _sanitize_text(text: str) -> str:
        # Keep only XML 1.0-compatible chars to avoid Confluence storage-format 400s.
        if not text:
            return ""

        def valid_char(ch: str) -> bool:
            code = ord(ch)
            return (
                code == 0x9
                or code == 0xA
                or code == 0xD
                or 0x20 <= code <= 0xD7FF
                or 0xE000 <= code <= 0xFFFD
                or 0x10000 <= code <= 0x10FFFF
            )

        return "".join(ch for ch in text if valid_char(ch))

    @staticmethod
    def _p(text: str) -> str:
        safe_text = html.escape(ConfluenceFormatter._sanitize_text(text))
        return f"<p>{safe_text}</p>"

    @staticmethod
    def _h(level: int, text: str) -> str:
        safe = html.escape(ConfluenceFormatter._sanitize_text(text))
        return f"<h{level}>{safe}</h{level}>"

    @staticmethod
    def _code_block(code: str) -> str:
        safe = html.escape(ConfluenceFormatter._sanitize_text(code))
        return f"<pre><code>{safe}</code></pre>"

    @staticmethod
    def _list_block(items: list[str]) -> str:
        if not items:
            return ""
        return "\n".join(f"<p>- {html.escape(ConfluenceFormatter._sanitize_text(item))}</p>" for item in items)

    def to_pages(self, payload: DocumentationPayload, root_title: str) -> list[ConfluencePage]:
        pages: list[ConfluencePage] = []

        pages.append(self.build_ready_page(payload, root_title))

        pages.append(
            ConfluencePage(
                title="System Design Overview",
                body_storage="\n".join(
                    [
                        self._h(1, "System Design Overview"),
                        self._p(payload.system_design_overview or payload.architecture or payload.overview),
                        self._h(2, "Architecture Diagram"),
                        self._code_block(payload.architecture_diagram or "Unknown"),
                        self._h(2, "Execution Lifecycle"),
                        self._list_block(payload.execution_lifecycle) or self._p("Unknown"),
                    ]
                ),
                parent_title=root_title,
                labels=["ai-docs", "system-design"],
            )
        )

        pages.append(
            ConfluencePage(
                title="Requirements",
                body_storage="\n".join(
                    [
                        self._h(1, "Requirements"),
                        self._h(2, "Functional Requirements"),
                        self._p(payload.requirements_functional or "Unknown"),
                        self._h(2, "Non-Functional Requirements"),
                        self._p(payload.requirements_nonfunctional or "Unknown"),
                        self._h(2, "Dependencies"),
                        self._list_block(payload.requirements_dependencies) or self._p("Unknown"),
                    ]
                ),
                parent_title=root_title,
                labels=["ai-docs", "requirements"],
            )
        )

        pages.append(
            ConfluencePage(
                title="Usage Guide",
                body_storage="\n".join(
                    [
                        self._h(1, "How to Use"),
                        self._p(payload.usage_overview or payload.subtitle or "Unknown"),
                        self._h(2, "Quick Start"),
                        self._list_block(payload.quick_start) or self._p("Unknown"),
                                self._h(2, "Usage Flow"),
                        self._list_block(payload.usage_guide) or self._p("Unknown"),
                    ]
                ),
                parent_title=root_title,
                labels=["ai-docs", "usage"],
            )
        )

        pages.append(
            ConfluencePage(
                title="Execution Lifecycle",
                body_storage="\n".join(
                    [
                        self._h(1, "Execution Lifecycle"),
                        self._list_block(payload.execution_lifecycle) or self._p("Unknown"),
                        self._h(2, "Summary"),
                        self._p(payload.summary or payload.developer_notes or "Unknown"),
                    ]
                ),
                parent_title=root_title,
                labels=["ai-docs", "lifecycle"],
            )
        )

        modules_body_parts = [self._h(1, "Modules")]
        for module in payload.modules:
            modules_body_parts.append(self._h(2, module.module))
            modules_body_parts.append(self._p(module.purpose))
            modules_body_parts.append(self._h(3, "Functions"))
            modules_body_parts.append(self._code_block("\n".join(module.functions) or "No functions found"))
            modules_body_parts.append(self._h(3, "Dependencies"))
            modules_body_parts.append(
                self._code_block("\n".join(module.dependencies) or "No dependencies found")
            )

        pages.append(
            ConfluencePage(
                title="Modules",
                body_storage="\n".join(modules_body_parts),
                parent_title=root_title,
                labels=["ai-docs", "modules"],
            )
        )

        pages.append(
            ConfluencePage(
                title="API Documentation",
                body_storage="\n".join([self._h(1, "API Documentation"), self._p(payload.api_documentation)]),
                parent_title=root_title,
                labels=["ai-docs", "api"],
            )
        )

        pages.append(
            ConfluencePage(
                title="Setup Guide",
                body_storage="\n".join([self._h(1, "Setup Guide"), self._p(payload.setup_guide)]),
                parent_title=root_title,
                labels=["ai-docs", "setup"],
            )
        )

        pages.append(
            ConfluencePage(
                title="Developer Notes",
                body_storage="\n".join([self._h(1, "Developer Notes"), self._p(payload.developer_notes)]),
                parent_title=root_title,
                labels=["ai-docs", "notes"],
            )
        )

        return pages

    def build_ready_page(self, payload: DocumentationPayload, root_title: str) -> ConfluencePage:
        page_title = payload.title or root_title
        sections: list[str] = [
            self._h(1, page_title),
            self._p(payload.subtitle or f"Generated documentation for {payload.repository}."),
            self._h(2, "System Design Overview"),
            self._p(payload.system_design_overview or payload.architecture or payload.overview),
            self._h(2, "Requirements"),
            self._p(payload.requirements_functional or "Functional requirements are derived from repository evidence and current runtime behavior."),
            self._p(payload.requirements_nonfunctional or "Non-functional requirements emphasize clarity, reproducibility, and Confluence-friendly output."),
            self._p(
                "Dependencies: "
                + (
                    ", ".join(payload.requirements_dependencies)
                    if payload.requirements_dependencies
                    else "Unknown"
                )
            ),
            self._h(2, "How to Use"),
            self._h(2, "Usage Guide"),
            self._p(payload.usage_overview or payload.subtitle or "Unknown"),
            self._h(2, "System Execution Lifecycle"),
            self._list_block(payload.execution_lifecycle) or self._p("Unknown"),
            self._h(2, "Summary"),
            self._p(payload.summary or payload.developer_notes or "Unknown"),
        ]

        sections.extend([
            self._h(2, "Table of Contents"),
            self._list_block(payload.table_of_contents) or self._p("System Design Overview, Requirements, Usage Guide, System Execution Lifecycle, Summary"),
        ])

        sections.extend([
            self._h(2, "Overview"),
            self._p(payload.overview),
            self._h(2, "Architecture"),
            self._p(payload.architecture),
        ])

        if payload.mathematical_formulation:
            sections.extend([
                self._h(2, "Mathematical Formulation"),
                self._p(payload.mathematical_formulation),
            ])

        if payload.features:
            sections.extend([
                self._h(2, "Features"),
                self._list_block(payload.features),
            ])

        if payload.tech_stack:
            sections.extend([
                self._h(2, "Tech Stack"),
                self._list_block(payload.tech_stack),
            ])

        if payload.project_structure:
            sections.extend([
                self._h(2, "Project Structure"),
                self._p(payload.project_structure),
            ])

        if payload.quick_start:
            sections.extend([
                self._h(2, "Quick Start"),
                self._list_block(payload.quick_start),
            ])

        if payload.usage_guide:
            sections.extend([
                self._h(2, "Usage Guide"),
                self._p(payload.usage_overview or ""),
                self._list_block(payload.usage_guide),
            ])

        if payload.api_reference:
            sections.extend([
                self._h(2, "API Reference"),
                self._list_block(payload.api_reference),
            ])

        if payload.validation_testing:
            sections.extend([
                self._h(2, "Validation & Testing"),
                self._list_block(payload.validation_testing),
            ])

        if payload.performance_notes:
            sections.extend([
                self._h(2, "Performance Notes"),
                self._p(payload.performance_notes),
            ])

        if payload.roadmap_ideas:
            sections.extend([
                self._h(2, "Roadmap Ideas"),
                self._list_block(payload.roadmap_ideas),
            ])

        if payload.license:
            sections.extend([
                self._h(2, "License"),
                self._p(payload.license),
            ])

        # Add Use Case if available
        if payload.use_case:
            sections.extend([
                self._h(2, "Use Case & Target Users"),
                self._p(payload.use_case),
            ])

        # Add Key Features if available
        if payload.key_features:
            sections.extend([
                self._h(2, "Key Features"),
                self._p(payload.key_features),
            ])

        sections.append(self._h(2, "Modules"))

        modules_rendered = 0
        for module in payload.modules[: self.MAX_MODULES_IN_READY_PAGE]:
            modules_rendered += 1
            sections.extend(
                [
                    self._h(3, module.module),
                    self._p(module.purpose),
                    self._h(4, "Functions"),
                    self._code_block("\n".join(module.functions) or "No functions found"),
                    self._h(4, "Dependencies"),
                    self._code_block("\n".join(module.dependencies) or "No dependencies found"),
                ]
            )

        if len(payload.modules) > modules_rendered:
            remaining = len(payload.modules) - modules_rendered
            sections.append(self._p(f"... and {remaining} additional modules omitted from this page for size limits."))

        sections.extend(
            [
                self._h(2, "API Documentation"),
                self._p(payload.api_documentation),
                self._h(2, "Setup Guide"),
                self._p(payload.setup_guide),
                self._h(2, "Developer Notes"),
                self._p(payload.developer_notes),
            ]
        )

        body = "\n".join(sections)
        if len(body) > self.MAX_READY_PAGE_CHARS:
            body = body[: self.MAX_READY_PAGE_CHARS]
            body += "\n" + self._p("Content truncated to fit Confluence page size limits.")

        return ConfluencePage(
            title=page_title,
            body_storage=body,
            labels=["ai-docs", "ready-to-publish"],
        )
