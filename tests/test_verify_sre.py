from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

import base64
import os
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("utf-8")


def _canonical_bytes(d: dict) -> bytes:
    payload = dict(d)
    payload.pop("signature", None)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sample_sre() -> dict:
    return {
        "assignment_id": "A1",
        "student_id": "CSE/24084",
        "repo_template": "basic-webapp",
        "round": 1,
        "deadline": datetime.now(timezone.utc).isoformat(),
        "nonce": "abc123",
        "signature": "",  # filled by test
    }


def test_verify_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Generate a fresh Ed25519 keypair
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path = tmp_path / "pub.pem"
    pub_path.write_bytes(pub_pem)

    # point verifier to this public key
    monkeypatch.setenv("SRE_PUBLIC_KEY_PATH", str(pub_path))

    # Build & sign SRE
    sre = _sample_sre()
    msg = _canonical_bytes(sre)
    sig = priv.sign(msg)
    sre["signature"] = _b64url_encode(sig)

    from student_agent.verify_sre import verify_sre
    ok, info = verify_sre(sre)
    assert ok, info


def test_verify_bad_sig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Generate keys but DO NOT sign correctly
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path = tmp_path / "pub.pem"
    pub_path.write_bytes(pub_pem)
    monkeypatch.setenv("SRE_PUBLIC_KEY_PATH", str(pub_path))

    sre = _sample_sre()
    # wrong signature (random bytes)
    sre["signature"] = _b64url_encode(b"not-a-real-signature")

    from student_agent.verify_sre import verify_sre
    ok, info = verify_sre(sre)
    assert not ok and "Signature" in info
