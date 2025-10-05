from __future__ import annotations

from typing import Tuple, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError


class SRE(BaseModel):
    """Minimal Signed Request Envelope schema (signature check is stubbed)."""
    assignment_id: str
    student_id: str
    repo_template: str | None = None
    round: int = Field(ge=1)
    deadline: datetime  # ISO 8601 string, e.g. 2025-10-15T23:59:59+05:30
    nonce: str | None = None
    signature: str


def _looks_like_base64url(s: str) -> bool:
    """Lightweight sanity check for base64url characters (no '=' padding needed)."""
    allowed = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    return len(s) > 8 and all(c in allowed for c in s)


def verify_sre(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate SRE fields (types & presence) and perform a basic signature sanity check.
    Replace the signature stub with real Ed25519/JOSE verification later.
    """
    try:
        sre = SRE.model_validate(data)  # Pydantic v2
    except ValidationError as e:
        return False, f"Schema validation failed: {e.errors()}"

    if not _looks_like_base64url(sre.signature):
        return False, "Signature is not base64url-like (stub check)."

    # TODO: Real signature verification using python-jose / cryptography.
    # Example (later):
    # from jose import jws
    # jws.verify(data_without_sig_json, sre.signature, public_key, algorithms=['EdDSA'])

    return True, "ok"
