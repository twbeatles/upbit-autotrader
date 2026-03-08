from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOVED_DOCS = (
    "PROJECT_STRUCTURE_ANALYSIS.md",
    "STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md",
)


def test_readme_and_claude_do_not_reference_removed_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    for doc in REMOVED_DOCS:
        assert doc not in readme, f"stale README reference: {doc}"
        assert doc not in claude, f"stale CLAUDE reference: {doc}"


def test_precommit_has_docs_reference_guard():
    precommit = ROOT / ".pre-commit-config.yaml"
    assert precommit.exists(), "missing .pre-commit-config.yaml"
    text = precommit.read_text(encoding="utf-8")
    assert "tests/test_docs_references.py" in text
