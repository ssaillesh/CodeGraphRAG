def documentation_prompt(repo_name: str, module_summaries: list[dict], evidence: list[dict]) -> str:
    return f"""
You are a senior staff engineer writing high-signal repository documentation.

Your task is to generate accurate, implementation-aware docs from evidence.
Write clearly for developers. Avoid fluff and generic enterprise wording.

---

# REPOSITORY
{repo_name}

# MODULE SUMMARIES
{module_summaries}

# CODE EVIDENCE (ground truth)
{evidence}

---

# OBJECTIVE

Produce a structured JSON document that explains:
- What the code does and why it exists
- How modules/services communicate with each other
- How to run the project locally (quick start + setup)
- System design and execution lifecycle
- If RAG exists: embedding model, retrieval flow, and why this model is used
- APIs, key modules, and practical usage guidance

---

# REQUIREMENTS

1) Be evidence-first. If unknown, write "unknown".
2) Prefer concrete commands and file-backed facts.
3) Keep section text concise but informative.
4) For communication flow, explain component interactions (API -> pipeline -> vector store -> LLM -> output).
5) For RAG, explicitly identify:
   - embedding model name
   - retrieval/index mechanism
   - rationale for model choice (speed/quality/dimension tradeoff)
6) Return VALID JSON only. No markdown fences.

---

# JSON CONTRACT (must match exactly)

Return this exact top-level shape (same keys):

Return:

{{
"title": "",
"subtitle": "",
"table_of_contents": [],
"system_design_overview": "",
"architecture_diagram": "",
"requirements_functional": "",
"requirements_nonfunctional": "",
"requirements_dependencies": [],
"usage_overview": "",
"execution_lifecycle": [],
"summary": "",
"overview": "",
"architecture": "",
"mathematical_formulation": "Not applicable",
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
"modules": [
{{
"module": "",
"purpose": "",
"functions": [],
"dependencies": []
}}
],
"api_documentation": "",
"setup_guide": "",
"developer_notes": ""
}}

---

# ARCHITECTURE DIAGRAM FORMAT

Use Mermaid in `architecture_diagram` as a string. Keep it compact and readable.
Example:
graph TD; A[API] --> B[Pipeline]; B --> C[Retriever]; C --> D[Vector Store]; B --> E[LLM]

---

# QUALITY BAR

- Provide a real run path in `quick_start` with concrete commands when evidence supports it.
- In `system_design_overview` and `architecture`, explain real component communication.
- In `performance_notes`, mention known tradeoffs (e.g., model size vs speed).
- Keep `modules` useful: include purpose, key functions, and meaningful dependencies only.
- Do not write meta phrases like "this documentation" or "this page will explain". Write direct technical explanations of the repository itself.

---

Now generate the documentation.
""".strip()
