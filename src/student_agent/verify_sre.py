from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

from pydantic import BaseModel, Field, ValidationError

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


class SRE(BaseModel):
    """Minimal Signed Request Envelope schema."""
    assignment_id: str
    student_id: str
    repo_template: str | None = None
    round: int = Field(ge=1)
    deadline: datetime            # validate that it's a valid ISO 8601 datetime
    nonce: str | None = None
    signature: str                # base64url-encoded Ed25519 signature


def _b64url_decode(s: str) -> bytes:
    pad = (-len(s)) % 4
    return base64.urlsafe_b64decode((s + ("=" * pad)).encode("utf-8"))


def _canonical_bytes(payload: Dict[str, Any]) -> bytes:
    """
    Deterministic bytes for signing/verifying:
      - remove 'signature'
      - JSON with sorted keys, no spaces
    NOTE: We canonicalize the **original incoming dict** so textual fields
    (like ISO datetimes) are preserved exactly as signed by the issuer.
    """
    d = dict(payload)
    d.pop("signature", None)
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _load_public_key_from_pem(path: Path) -> Ed25519PublicKey:
    data = path.read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("Public key is not Ed25519.")
    return key


def verify_sre(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate SRE schema and verify Ed25519 signature against canonical JSON bytes."""
    # 1) Schema/type validation (parses 'deadline' but doesn't change the source dict)
    try:
        SRE.model_validate(data)  # Pydantic v2
    except ValidationError as e:
        return False, f"Schema validation failed: {e.errors()}"

    # 2) Load public key
    pub_path_env = os.getenv("SRE_PUBLIC_KEY_PATH")
    if not pub_path_env:
        return False, "SRE_PUBLIC_KEY_PATH is not set (path to PEM Ed25519 public key)."
    pub_path = Path(pub_path_env)
    if not pub_path.exists():
        return False, f"Public key not found at: {pub_path}"
    try:
        pub = _load_public_key_from_pem(pub_path)
    except Exception as ex:
        return False, f"Failed to load public key: {ex}"

    # 3) Decode signature
    try:
        sig = _b64url_decode(str(data.get("signature", "")))
    except Exception:
        return False, "Signature is not valid base64url."

    # 4) Canonicalize the **original** dict (preserves exact deadline string, etc.)
    message = _canonical_bytes(data)

    # 5) Verify
    try:
        pub.verify(sig, message)
    except Exception:
        return False, "Signature verification failed."

    return True, "ok"
