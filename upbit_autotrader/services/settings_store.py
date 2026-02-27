"""
Settings store with schema migration and DPAPI credential handling.
"""

import json
import os
from typing import Dict, Any

from upbit_autotrader.services.security import encrypt_dpapi, decrypt_dpapi, DPAPIError


SETTINGS_VERSION = 2


def load_settings(path: str) -> Dict[str, Any]:
    """Load settings and normalize API credential fields."""
    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    normalized = dict(data)
    normalized["_credential_error"] = None

    api_credentials = data.get("api_credentials", {})
    if isinstance(api_credentials, dict) and api_credentials.get("storage") == "dpapi":
        access_enc = api_credentials.get("access_enc", "")
        secret_enc = api_credentials.get("secret_enc", "")
        try:
            normalized["access_key"] = decrypt_dpapi(access_enc) if access_enc else ""
            normalized["secret_key"] = decrypt_dpapi(secret_enc) if secret_enc else ""
        except DPAPIError as exc:
            normalized["access_key"] = ""
            normalized["secret_key"] = ""
            normalized["_credential_error"] = str(exc)
    else:
        # Legacy plain-text schema
        normalized["access_key"] = data.get("access_key", "")
        normalized["secret_key"] = data.get("secret_key", "")

    return normalized


def save_settings(path: str, settings: Dict[str, Any]) -> None:
    """Save settings in v2 schema with DPAPI-protected credentials."""
    payload = dict(settings)

    access_key = str(payload.pop("access_key", "") or "").strip()
    secret_key = str(payload.pop("secret_key", "") or "").strip()
    payload.pop("_credential_error", None)

    payload["settings_version"] = SETTINGS_VERSION
    payload["api_credentials"] = {
        "storage": "dpapi",
        "access_enc": encrypt_dpapi(access_key) if access_key else "",
        "secret_enc": encrypt_dpapi(secret_key) if secret_key else "",
    }

    # Legacy plain-text credentials are migration-only; never persist in v2.
    payload.pop("access_key", None)
    payload.pop("secret_key", None)

    with open(path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


