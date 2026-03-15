from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REMOVED_DOCS = (
    "PROJECT_STRUCTURE_ANALYSIS.md",
    "STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md",
)
GUIDE_DOCS = (
    "README.md",
    "CLAUDE.md",
    "GEMINI.md",
)
CURRENT_REFERENCED_DOCS = (
    "IMPLEMENTATION_RISK_REVIEW_2026-03-08.md",
    "legacy_wrappers/README.md",
)


def test_readme_and_claude_do_not_reference_removed_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    for doc in REMOVED_DOCS:
        assert doc not in readme, f"stale README reference: {doc}"
        assert doc not in claude, f"stale CLAUDE reference: {doc}"


def test_guide_docs_reference_existing_current_docs():
    for doc in CURRENT_REFERENCED_DOCS:
        assert (ROOT / doc).exists(), f"missing referenced doc: {doc}"

    for guide in GUIDE_DOCS:
        text = (ROOT / guide).read_text(encoding="utf-8")
        for doc in CURRENT_REFERENCED_DOCS:
            assert doc in text, f"{guide} missing current doc reference: {doc}"


def test_guide_docs_include_quality_checks():
    for guide in GUIDE_DOCS:
        text = (ROOT / guide).read_text(encoding="utf-8")
        assert "python -m pyright" in text, f"{guide} missing pyright command"
        assert "pre-commit run --all-files" in text, f"{guide} missing pre-commit command"
        assert "tests/test_text_integrity.py" in text, f"{guide} missing text integrity reference"


def test_precommit_has_docs_reference_guard():
    precommit = ROOT / ".pre-commit-config.yaml"
    assert precommit.exists(), "missing .pre-commit-config.yaml"
    text = precommit.read_text(encoding="utf-8")
    assert "tests/test_docs_references.py" in text
