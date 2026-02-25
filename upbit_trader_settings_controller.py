"""Compatibility wrapper for refactored module location."""

import importlib as _importlib
import sys as _sys

_impl = _importlib.import_module('upbit_autotrader.controllers.settings_controller')
_impl = _importlib.reload(_impl)
_sys.modules[__name__] = _impl

