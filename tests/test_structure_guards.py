import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

FILE_LINE_LIMITS = {
    "upbit_autotrader/controllers/trading_controller.py": 3000,
    "upbit_autotrader/controllers/ui_controller.py": 700,
    "upbit_autotrader/controllers/settings_controller.py": 240,
    "upbit_autotrader/controllers/batch_controller.py": 360,
    "upbit_autotrader/strategies/legacy_strategy.py": 600,
}

CLASS_METHOD_LINE_LIMITS = {
    "upbit_autotrader/controllers/trading_controller.py": 240,
    "upbit_autotrader/controllers/ui_controller.py": 140,
    "upbit_autotrader/controllers/settings_controller.py": 120,
    "upbit_autotrader/controllers/batch_controller.py": 130,
    "upbit_autotrader/strategies/legacy_strategy.py": 120,
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_refactor_file_line_limits_guard():
    for rel_path, limit in FILE_LINE_LIMITS.items():
        path = REPO_ROOT / rel_path
        line_count = len(_read(path).splitlines())
        assert line_count <= limit, f"{rel_path} has {line_count} lines (limit: {limit})"


def test_refactor_method_line_limits_guard():
    for rel_path, limit in CLASS_METHOD_LINE_LIMITS.items():
        path = REPO_ROOT / rel_path
        source = _read(path)
        mod = ast.parse(source)
        classes = [node for node in mod.body if isinstance(node, ast.ClassDef)]
        if not classes:
            continue
        methods = []
        for cls in classes:
            methods.extend(
                node for node in cls.body if isinstance(node, ast.FunctionDef) and node.end_lineno is not None
            )
        if not methods:
            continue
        longest = max(methods, key=lambda node: (node.end_lineno - node.lineno + 1))
        longest_len = longest.end_lineno - longest.lineno + 1
        assert (
            longest_len <= limit
        ), f"{rel_path} longest method {longest.name} is {longest_len} lines (limit: {limit})"
