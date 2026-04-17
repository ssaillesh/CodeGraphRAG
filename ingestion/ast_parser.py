import ast
from dataclasses import dataclass

from ingestion.file_parser import FileDocument
from tree_sitter_languages import get_parser


@dataclass
class SymbolInfo:
    name: str
    symbol_type: str
    line: int


class ASTParser:
    TREE_SITTER_LANGUAGE_MAP = {
        "javascript": "javascript",
        "typescript": "typescript",
        "java": "java",
        "go": "go",
        "rust": "rust",
    }

    def extract_symbols(self, file_doc: FileDocument) -> list[SymbolInfo]:
        if file_doc.language == "python":
            return self._parse_python(file_doc)
        if file_doc.language in self.TREE_SITTER_LANGUAGE_MAP:
            tree_sitter_symbols = self._parse_with_tree_sitter(file_doc)
            if tree_sitter_symbols:
                return tree_sitter_symbols
        return self._fallback_symbol_scan(file_doc)

    def _parse_python(self, file_doc: FileDocument) -> list[SymbolInfo]:
        try:
            tree = ast.parse(file_doc.content)
        except SyntaxError:
            return []

        symbols: list[SymbolInfo] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(SymbolInfo(name=node.name, symbol_type="class", line=node.lineno))
            elif isinstance(node, ast.FunctionDef):
                symbols.append(SymbolInfo(name=node.name, symbol_type="function", line=node.lineno))
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append(
                    SymbolInfo(name=node.name, symbol_type="async_function", line=node.lineno)
                )
        return symbols

    def _fallback_symbol_scan(self, file_doc: FileDocument) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        lines = file_doc.content.splitlines()
        for index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("class "):
                name = stripped.split()[1].split("(")[0].rstrip(":")
                symbols.append(SymbolInfo(name=name, symbol_type="class", line=index))
            elif stripped.startswith("def "):
                name = stripped.split()[1].split("(")[0].rstrip(":")
                symbols.append(SymbolInfo(name=name, symbol_type="function", line=index))
        return symbols

    def _parse_with_tree_sitter(self, file_doc: FileDocument) -> list[SymbolInfo]:
        try:
            parser = get_parser(self.TREE_SITTER_LANGUAGE_MAP[file_doc.language])
            tree = parser.parse(file_doc.content.encode("utf-8"))
        except Exception:
            return []

        symbols: list[SymbolInfo] = []

        def visit(node):
            node_type = node.type
            if node_type in {
                "class_declaration",
                "class_definition",
                "function_declaration",
                "function_definition",
                "method_definition",
            }:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = file_doc.content[name_node.start_byte : name_node.end_byte]
                    symbols.append(
                        SymbolInfo(
                            name=name,
                            symbol_type="class" if "class" in node_type else "function",
                            line=node.start_point[0] + 1,
                        )
                    )

            for child in node.children:
                visit(child)

        visit(tree.root_node)
        return symbols
