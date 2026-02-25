"""Compatibility entrypoint for refactored application package."""

from upbit_autotrader.app.trader import *  # noqa: F401,F403
from upbit_autotrader.app.trader import main as _main

if __name__ == "__main__":
    _main()

