"""Legacy wrapper for upbit_client."""

import sys
from upbit_autotrader.services.upbit_client import UpbitRestClient

sys.modules[__name__] = sys.modules["upbit_autotrader.services.upbit_client"]
