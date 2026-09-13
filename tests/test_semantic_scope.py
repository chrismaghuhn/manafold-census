import ast
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_ROOT = REPOSITORY_ROOT / "src" / "manafold_census" / "semantic"

FORBIDDEN_IMPORT_COMPONENTS = {
    "anthropic",
    "asyncpg",
    "database",
    "engine",
    "httpx",
    "json",
    "langchain",
    "litellm",
    "llama_index",
    "openai",
    "psycopg",
    "pymongo",
    "pathlib",
    "requests",
    "rust",
    "sqlalchemy",
    "sqlite3",
    "subprocess",
    "transformers",
    "urllib",
    "gzip",
    "os",
}
FORBIDDEN_DECLARATIONS = re.compile(
    r"\b(?:Capability(?:Family)?|capability_id|CardAnalysisRecord|"
    r"engine_support|coverage_percentage)\b",
    re.IGNORECASE,
)
FORBIDDEN_EXECUTION_NAMES = re.compile(
    r"\b(?:download|fetch|glob|iterdir|listdir|open|read_bytes|read_text|"
    r"rglob|urlopen|walk)\s*\(",
    re.IGNORECASE,
)
FORBIDDEN_SCOPE_REFERENCES = re.compile(
    r"(?:\.github|ci\.yml|justfile|cli\.py|global\s+corpus|38,?740|"
    r"implement_card|execute_card|card_executor|card_specific)",
    re.IGNORECASE,
)


def _semantic_modules() -> list[Path]:
    return sorted(SEMANTIC_ROOT.glob("*.py"))


def _import_targets(tree: ast.AST) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                targets.append(node.module)
            targets.extend(alias.name for alias in node.names)
    return targets


def test_semantic_modules_have_no_engine_network_database_or_llm_imports() -> None:
    modules = _semantic_modules()
    assert modules
    for module in modules:
        tree = ast.parse(module.read_text(encoding="utf-8"), filename=str(module))
        for target in _import_targets(tree):
            components = set(target.lower().split("."))
            assert components.isdisjoint(FORBIDDEN_IMPORT_COMPONENTS), (
                f"{module.relative_to(REPOSITORY_ROOT)} imports forbidden dependency "
                f"{target}"
            )


def test_semantic_modules_do_not_define_capabilities_or_card_analysis() -> None:
    for module in _semantic_modules():
        text = module.read_text(encoding="utf-8")
        assert FORBIDDEN_DECLARATIONS.search(text) is None, (
            f"{module.relative_to(REPOSITORY_ROOT)} introduces a later-milestone "
            "capability or card-analysis vocabulary"
        )


def test_semantic_modules_do_not_acquire_or_enumerate_the_global_corpus() -> None:
    for module in _semantic_modules():
        text = module.read_text(encoding="utf-8")
        assert FORBIDDEN_EXECUTION_NAMES.search(text) is None, (
            f"{module.relative_to(REPOSITORY_ROOT)} performs source acquisition or "
            "filesystem corpus enumeration"
        )
        assert "38740" not in text
        assert "38,740" not in text


def test_m2_semantic_scope_excludes_cli_ci_justfile_and_global_artifacts() -> None:
    for module in _semantic_modules():
        text = module.read_text(encoding="utf-8")
        assert FORBIDDEN_SCOPE_REFERENCES.search(text) is None, (
            f"{module.relative_to(REPOSITORY_ROOT)} crosses the M2 boundary"
        )

    tracked_paths = subprocess.check_output(
        ["git", "ls-files"], cwd=REPOSITORY_ROOT, text=True
    ).splitlines()
    assert not any(path.startswith(("dist/", ".cache/")) for path in tracked_paths)
    assert {
        path for path in tracked_paths if path.startswith("fixtures/semantic/")
    } == {"fixtures/semantic/representative-bundles.json"}
