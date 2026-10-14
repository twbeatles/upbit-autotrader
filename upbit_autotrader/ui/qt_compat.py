"""Qt binding consistency guard.

``qfluentwidgets`` ships per-binding distributions (one per Qt binding)
under a single import namespace. If the importable build targets a different
binding than this application's PySide6, its classes must never be mixed into
PySide6 parents -- PySide6 rejects such instances with ``TypeError`` (e.g. in
``QTimer``/``QThread`` constructors). Every ``qfluentwidgets`` use site must
go through :func:`fluent_window_base`, which returns a class only when it is
a genuine PySide6 widget subclass.
"""

from __future__ import annotations

from typing import Any


def is_pyside6_widget_class(cls: Any) -> bool:
    """True when *cls* is a PySide6 QWidget subclass (safe as a Qt parent)."""
    try:
        from PySide6.QtWidgets import QWidget

        return isinstance(cls, type) and issubclass(cls, QWidget)
    except Exception:
        return False


def fluent_window_base() -> type[Any] | None:
    """PySide6-bound Fluent/MSFluent window class, else None (use QMainWindow)."""
    try:
        from qfluentwidgets import FluentWindow as candidate
    except ImportError:
        candidate = None
    if candidate is not None and is_pyside6_widget_class(candidate):
        return candidate
    try:
        from qfluentwidgets import MSFluentWindow as candidate  # type: ignore[no-redef]
    except ImportError:
        return None
    if candidate is not None and is_pyside6_widget_class(candidate):
        return candidate
    return None
