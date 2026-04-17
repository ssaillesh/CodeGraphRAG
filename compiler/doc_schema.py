from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ModuleDoc(BaseModel):
    module: str
    purpose: str
    functions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class DocumentationPayload(BaseModel):
    repository: str
    title: str = ""
    subtitle: str = ""
    table_of_contents: list[str] = Field(default_factory=list)
    system_design_overview: str = ""
    architecture_diagram: str = ""
    requirements_functional: str = ""
    requirements_nonfunctional: str = ""
    requirements_dependencies: list[str] = Field(default_factory=list)
    usage_overview: str = ""
    execution_lifecycle: list[str] = Field(default_factory=list)
    summary: str = ""
    overview: str  # What does the codebase do
    architecture: str  # How is it organized
    mathematical_formulation: str = ""
    features: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    project_structure: str = ""
    quick_start: list[str] = Field(default_factory=list)
    usage_guide: list[str] = Field(default_factory=list)
    api_reference: list[str] = Field(default_factory=list)
    validation_testing: list[str] = Field(default_factory=list)
    performance_notes: str = ""
    roadmap_ideas: list[str] = Field(default_factory=list)
    license: str = ""
    use_case: str = ""  # Who uses it and why
    key_features: str = ""  # Main capabilities
    modules: list[ModuleDoc] = Field(default_factory=list)
    api_documentation: str
    setup_guide: str
    developer_notes: str


class ConfluencePage(BaseModel):
    title: str
    body_storage: str
    parent_title: Optional[str] = None
    labels: list[str] = Field(default_factory=list)


class ConfluencePublishResult(BaseModel):
    title: str
    page_id: str
    status: str
