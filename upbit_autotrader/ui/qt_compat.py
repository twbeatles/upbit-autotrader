"""Qt binding consistency guard.

``qfluentwidgets`` ships per-binding distributions (PyQt6, PySide6, ...)
under a single import namespace. If the importable build targets a different
binding than this application's PyQt6, its classes must never be mixed into
PyQt6 parents -- PyQt6 rejects such instances with ``TypeError`` (e.g. in
``QTimer``/``QThread`` constructors). Every ``qfluentwidgets`` use site must
go through :func:`fluent_window_base`, which returns a class only when it is
a genuine PyQt6 widget subclass.
"""

from __future__ import annotations

from typing import Any


def is_pyqt6_widget_class(cls: Any) -> bool:
    """True when *cls* is a PyQt6 QWidget subclass (safe as a Qt parent)."""
    try:
        from PyQt6.QtWidgets import QWidget

        return isinstance(cls, type) and issubclass(cls, QWidget)
    except Exception:
        return False


def fluent_window_base() -> type[Any] | None:
    """PyQt6-bound Fluent/MSFluent window class, else None (use QMainWindow)."""
    try:
        from qfluentwidgets import FluentWindow as candidate
    except ImportError:
        candidate = None
    if candidate is not None and is_pyqt6_widget_class(candidate):
        return candidate
    try:
        from qfluentwidgets import MSFluentWindow as candidate  # type: ignore[no-redef]
    except ImportError:
        return None
    if candidate is not None and is_pyqt6_widget_class(candidate):
        return candidate
    return None
