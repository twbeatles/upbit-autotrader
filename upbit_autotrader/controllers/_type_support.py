from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow

    class ControllerTypeBase(QMainWindow):
        def __getattr__(self, name: str) -> Any: ...

else:
    class ControllerTypeBase:
        pass
