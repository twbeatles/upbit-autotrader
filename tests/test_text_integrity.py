from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIRS = ("upbit_autotrader", "legacy_wrappers", "tests")
ROOT_TEXT_PATTERNS = ("*.md", "*.txt", "*.yaml", "*.yml", "*.json", "*.spec")
ROOT_DOTFILES = (".gitignore", ".pre-commit-config.yaml")
QUESTION_PLACEHOLDER = "?" * 2
REPLACEMENT_CHAR = "\ufffd"
ALLOWED_PLACEHOLDER_LINES: dict[str, tuple[str, ...]] = {}


def _iter_target_files() -> list[Path]:
    files: set[Path] = set()

    for directory in PYTHON_DIRS:
        files.update((ROOT / directory).rglob("*.py"))

    for pattern in ROOT_TEXT_PATTERNS:
        files.update(path for path in ROOT.glob(pattern) if path.is_file())

    for name in ROOT_DOTFILES:
        path = ROOT / name
        if path.exists():
            files.add(path)

    return sorted(files)


def _is_allowed_placeholder(relative_path: str, line: str) -> bool:
    return any(fragment in line for fragment in ALLOWED_PLACEHOLDER_LINES.get(relative_path, ()))


def test_repository_text_files_are_utf8_and_have_no_placeholder_garbles():
    issues: list[str] = []

    for path in _iter_target_files():
        relative_path = path.relative_to(ROOT).as_posix()

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            issues.append(f"{relative_path}: utf-8 decode failed ({exc})")
            continue

        if REPLACEMENT_CHAR in text:
            issues.append(f"{relative_path}: contains replacement character U+FFFD")

        for line_number, line in enumerate(text.splitlines(), 1):
            if QUESTION_PLACEHOLDER in line and not _is_allowed_placeholder(relative_path, line):
                issues.append(
                    f"{relative_path}:{line_number}: contains repeated question-mark placeholder"
                )

    assert not issues, "text integrity issues found:\n" + "\n".join(issues)
