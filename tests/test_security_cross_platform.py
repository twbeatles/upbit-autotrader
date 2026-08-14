"""Tests for cross-platform security DPAPI fallback and exception safety."""

import ctypes
from unittest.mock import patch
import pytest

from upbit_autotrader.services.security import encrypt_dpapi, decrypt_dpapi, DPAPIError


def test_security_dpapi_error_on_non_windows():
    # Simulate non-Windows environment where ctypes has no windll
    with patch("upbit_autotrader.services.security.getattr", return_value=None):
        with pytest.raises(DPAPIError) as exc_info:
            encrypt_dpapi("my_secret_key")
        assert "DPAPI is only available on Windows" in str(exc_info.value)

        with pytest.raises(DPAPIError) as exc_info:
            decrypt_dpapi("fake_cipher_b64")
        assert "DPAPI is only available on Windows" in str(exc_info.value)
