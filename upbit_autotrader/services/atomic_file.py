"""Atomic JSON file writes shared by all local persistence paths.

Single-threaded GUI timers and `closeEvent` flush several JSON state files.
A direct `open(path, "w")` + `json.dump` can leave a truncated file when the
process is killed mid-write; every persistent JSON write must go through
:func:`write_json_atomic` (tmp file + ``os.replace``) instead.
"""

from __future__ import annotations

import json
import os
from typing import Any


def write_json_atomic(path: str, payload: Any) -> bool:
    """Write *payload* as JSON atomically. Returns True on success."""
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False
