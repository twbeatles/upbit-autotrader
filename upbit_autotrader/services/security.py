"""
Windows DPAPI helpers for protecting API credentials.
"""

import base64
import ctypes
from ctypes import wintypes


CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


class DPAPIError(RuntimeError):
    """Raised when DPAPI encryption/decryption fails."""


def _bytes_to_blob(data: bytes) -> DATA_BLOB:
    if not data:
        return DATA_BLOB(0, None)

    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB()
    blob.cbData = len(data)
    blob.pbData = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))
    blob._buffer = buffer  # keep alive while API call executes
    return blob


def _blob_to_bytes(blob: DATA_BLOB) -> bytes:
    if not blob.cbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def encrypt_dpapi(text: str) -> str:
    """Encrypt plain text with Windows DPAPI and return base64 text."""
    if text is None:
        text = ""

    windll = getattr(ctypes, "windll", None)
    if windll is None or not hasattr(windll, "crypt32"):
        raise DPAPIError("DPAPI is only available on Windows.")

    crypt32 = windll.crypt32
    kernel32 = windll.kernel32

    input_blob = _bytes_to_blob(text.encode("utf-8"))
    output_blob = DATA_BLOB()

    ok = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise DPAPIError(f"DPAPI encryption failed (code={kernel32.GetLastError()}).")

    try:
        encrypted = _blob_to_bytes(output_blob)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)


def decrypt_dpapi(cipher_b64: str) -> str:
    """Decrypt base64 DPAPI cipher text and return plain text."""
    if not cipher_b64:
        return ""

    windll = getattr(ctypes, "windll", None)
    if windll is None or not hasattr(windll, "crypt32"):
        raise DPAPIError("DPAPI is only available on Windows.")

    crypt32 = windll.crypt32
    kernel32 = windll.kernel32

    try:
        encrypted_bytes = base64.b64decode(cipher_b64.encode("ascii"))
    except Exception as exc:
        raise DPAPIError(f"Invalid DPAPI base64 payload: {exc}") from exc

    input_blob = _bytes_to_blob(encrypted_bytes)
    output_blob = DATA_BLOB()

    ok = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise DPAPIError(f"DPAPI decryption failed (code={kernel32.GetLastError()}).")

    try:
        decrypted = _blob_to_bytes(output_blob)
        return decrypted.decode("utf-8")
    except Exception as exc:
        raise DPAPIError(f"Failed to decode decrypted bytes: {exc}") from exc
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)

