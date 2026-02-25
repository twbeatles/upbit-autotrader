from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readme_and_claude_reference_required_docs_and_files_exist():
    required_docs = [
        "PROJECT_STRUCTURE_ANALYSIS.md",
        "STRATEGY_OPTIONS_IMPLEMENTATION_PLAN.md",
    ]

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")

    for doc in required_docs:
        assert doc in readme
        assert doc in claude
        assert (ROOT / doc).exists(), f"missing document: {doc}"
