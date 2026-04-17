from pathlib import Path

from ingestion.ast_parser import ASTParser
from ingestion.file_parser import FileDocument


def test_python_symbol_extraction(tmp_path: Path) -> None:
    parser = ASTParser()
    sample = FileDocument(
        path=tmp_path / "sample.py",
        relative_path="sample.py",
        language="python",
        content="class Service:\n    pass\n\n\ndef run():\n    return 1\n",
        sha256="dummy",
    )

    symbols = parser.extract_symbols(sample)
    symbol_names = {s.name for s in symbols}
    assert "Service" in symbol_names
    assert "run" in symbol_names
