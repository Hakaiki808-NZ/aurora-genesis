"""Aurora Nitro Enclaves attestation verification reference.

Standalone fail-closed verifier for AWS Nitro COSE_Sign1 / NSM documents.
This is NOT integrated into the private Aurora Engine; a deployment must
add atomic one-use nonce admission, trusted PCR enrollment and host tests.

The production entry point always pins the documented AWS commercial
Nitro Enclaves root SHA256; root input is never accepted as trust itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
from io import BytesIO
from pathlib import Path
import time
from typing import Mapping

import cbor2
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa, utils

# AWS Nitro Enclaves Root G1 SHA-256 fingerprint, as published in AWS docs:
# https://docs.aws.amazon.com/enclaves/latest/user/verify-root.html
AWS_NITRO_ROOT_SHA256 = (
    "641a0321a3e244efe456463195d606317ed7cdcc3c1756e09893f3c68f79bb5b"
)
MAX_DOCUMENT_BYTES = 16 * 1024
MAX_AGE_MS = 90_000
REQUIRED_PCRS = frozenset({0, 1, 2, 3, 4, 8})


class AttestationDenied(ValueError):
    """Reject an untrusted, malformed, mismatched or stale document."""


@dataclass(frozen=True)
class VerifiedEnclave:
    module_id: str
    timestamp_ms: int
    pcrs_hex: dict[int, str]
    enclave_public_key: bytes


def _decode_one(raw: bytes):
    buffer = BytesIO(raw)
    val = cbor2.CBORDecoder(buffer).decode()
    if buffer.read(1):
        raise AttestationDenied("trailing CBOR bytes")
    return val


def _require(condition: bool, msg: str) -> None:
    if not condition:
        raise AttestationDenied(msg)


def _valid_time(cert: x509.Certificate, instant: datetime) -> None:
    # Only the pinned AWS root and certificates in its verified chain count.
    try:
        start, end = cert.not_valid_before_utc, cert.not_valid_after_utc
    except AttributeError:  # older cryptography versions
        start = cert.not_valid_before.replace(tzinfo=timezone.utc)
        end = cert.not_valid_after.replace(tzinfo=timezone.utc)
    _require(start <= instant <= end, "certificate outside validity period")


def _verify_child_cert(child: x509.Certificate, issuer: x509.Certificate) -> None:
    _require(child.issuer == issuer.subject, "certificate issuer mismatch")
    try:
        constraints = issuer.extensions.get_extension_for_class(
            x509.BasicConstraints
        ).value
    except x509.ExtensionNotFound as exc:
        raise AttestationDenied("issuer is not a CA") from exc
    _require(constraints.ca, "issuer is not a CA")
    try:
        usage = issuer.extensions.get_extension_for_class(x509.KeyUsage).value
        _require(usage.key_cert_sign, "issuer cannot sign certificates")
    except x509.ExtensionNotFound:
        pass
    key = issuer.public_key()
    try:
        if isinstance(key, ec.EllipticCurvePublicKey):
            key.verify(child.signature, child.tbs_certificate_bytes,
                       ec.ECDSA(child.signature_hash_algorithm))
        elif isinstance(key, rsa.RSAPublicKey):
            key.verify(child.signature, child.tbs_certificate_bytes,
                       padding.PKCS1v15(), child.signature_hash_algorithm)
        else:
            raise AttestationDenied("unsupported certificate issuer key")
    except Exception as exc:
        raise AttestationDenied("certificate signature verification failed") from exc


def _verify_chain(
    leaf_der: bytes, bundle: list[bytes], root_der: bytes,
    root_digest: str, instant: datetime,
) -> x509.Certificate:
    # A root DER file is supplied separately, then authenticated by its
    # compile-time pin. The document cannot bring a new trust anchor.
    _require(hmac.compare_digest(hashlib.sha256(root_der).hexdigest(), root_digest),
             "untrusted root fingerprint")
    try:
        root = x509.load_der_x509_certificate(root_der)
        leaf = x509.load_der_x509_certificate(leaf_der)
        candidates = [x509.load_der_x509_certificate(x) for x in bundle]
    except (ValueError, TypeError) as exc:
        raise AttestationDenied("invalid X509 certificate") from exc
    _require(len(candidates) <= 8, "certificate chain too long")
    _valid_time(root, instant)
    _valid_time(leaf, instant)
    try:
        usage = leaf.extensions.get_extension_for_class(x509.KeyUsage).value
        _require(usage.digital_signature, "leaf cannot sign attestation")
    except x509.ExtensionNotFound:
        pass

    # Follow exact issuer relationships; no untrusted alternate root.
    seen = set()
    current = leaf
    for _ in range(len(candidates) + 2):
        digest = current.fingerprint(hashes.SHA256())
        _require(digest not in seen, "certificate chain loop")
        seen.add(digest)
        if current.issuer == root.subject:
            _verify_child_cert(current, root)
            return leaf
        matching = [c for c in candidates if c.subject == current.issuer]
        _require(len(matching) == 1, "ambiguous or incomplete certificate chain")
        parent = matching[0]
        _valid_time(parent, instant)
        _verify_child_cert(current, parent)
        current = parent
    raise AttestationDenied("certificate chain did not reach pinned AWS root")


def _verify(
    document: bytes, *, root_der: bytes, root_digest: str,
    expected_nonce: bytes, expected_pcrs: Mapping[int, bytes],
    expected_user_data: bytes, expected_public_key: bytes,
    now_ms: int,
) -> VerifiedEnclave:
    _require(type(document) is bytes and 0 < len(document) <= MAX_DOCUMENT_BYTES,
             "document length")
    _require(type(expected_nonce) is bytes and 16 <= len(expected_nonce) <= 64,
             "fresh nontrivial Engine challenge is required")
    _require(type(expected_user_data) is bytes and len(expected_user_data) >= 16,
             "Engine epoch/task binding is required")
    _require(type(expected_public_key) is bytes and len(expected_public_key) >= 32,
             "enrolled Angel session key is required")
    _require(set(expected_pcrs) == REQUIRED_PCRS,
             "all approved PCR0,1,2,3,4,8 are required")
    for value in expected_pcrs.values():
        _require(type(value) is bytes and len(value) == 48 and any(value),
                 "invalid enrolled PCR")
    try:
        cose = _decode_one(document)
        if isinstance(cose, cbor2.CBORTag):
            _require(cose.tag == 18, "unexpected COSE tag")
            cose = cose.value
        _require(isinstance(cose, (list, tuple)) and len(cose) == 4, "COSE Sign1 shape")
        protected, unprotected, payload, signature = cose
        print("AURORA_VERIFY_DEBUG_CBOR_TYPES", type(cose).__name__, [type(v).__name__ for v in cose], flush=True)
        _require(type(protected) is bytes and type(unprotected) is dict
                 and type(payload) is bytes and type(signature) is bytes
                 and len(signature) == 96, "COSE field shape")
        hdr = _decode_one(protected)
        _require(type(hdr) is dict and hdr.get(1) == -35,
                 "only COSE ES384 accepted")
        _require(1 not in unprotected, "algorithm cannot be overridden")
        data = _decode_one(payload)
        _require(type(data) is dict and data.get("digest") == "SHA384",
                 "invalid Nitro payload")
        ts = data.get("timestamp")
        _require(type(ts) is int and abs(now_ms - ts) <= MAX_AGE_MS,
                 "stale or future attestation")
        _require(type(data.get("nonce")) is bytes
                 and hmac.compare_digest(data["nonce"], expected_nonce),
                 "nonce mismatch")
        _require(type(data.get("user_data")) is bytes
                 and hmac.compare_digest(data["user_data"], expected_user_data),
                 "Engine epoch/task binding mismatch")
        pub = data.get("public_key")
        _require(type(pub) is bytes and hmac.compare_digest(pub, expected_public_key),
                 "Angel session key mismatch")
        pcrs = data.get("pcrs")
        _require(type(pcrs) is dict, "PCR map missing")
        for key in REQUIRED_PCRS:
            value = pcrs.get(key)
            _require(type(value) is bytes and len(value) == 48 and any(value),
                     "missing or zero (debug-mode) PCR")
            _require(hmac.compare_digest(value, expected_pcrs[key]),
                     "enclave measurement mismatch")
        module_id = data.get("module_id")
        _require(type(module_id) is str and 1 <= len(module_id) <= 256,
                 "invalid Nitro module identity")
        leaf_der, bundle = data.get("certificate"), data.get("cabundle")
        _require(type(leaf_der) is bytes and type(bundle) is list
                 and all(type(v) is bytes for v in bundle),
                 "certificate chain missing")
        # Verify chain at the verifier's wall clock, not at the untrusted
        # timestamp supplied by the attestation document.
        instant = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc)
        cert = _verify_chain(leaf_der, bundle, root_der, root_digest, instant)
        key = cert.public_key()
        _require(isinstance(key, ec.EllipticCurvePublicKey)
                 and isinstance(key.curve, ec.SECP384R1),
                 "Nitro COSE signing key must be P-384")
        signed = cbor2.dumps(["Signature1", protected, b"", payload])
        r = int.from_bytes(signature[:48], "big")
        s = int.from_bytes(signature[48:], "big")
        key.verify(utils.encode_dss_signature(r, s), signed,
                   ec.ECDSA(hashes.SHA384()))
        return VerifiedEnclave(
            module_id=module_id, timestamp_ms=ts,
            pcrs_hex={k:expected_pcrs[k].hex() for k in sorted(REQUIRED_PCRS)},
            enclave_public_key=pub,
        )
    except AttestationDenied:
        raise
    except Exception as exc:
        raise AttestationDenied("cryptographic attestation verification failed") from exc


def verify_nitro_angel(
    document: bytes, *, trusted_root_der_path: str | Path,
    expected_nonce: bytes, expected_pcrs: Mapping[int, bytes],
    expected_user_data: bytes, expected_public_key: bytes,
) -> VerifiedEnclave:
    """Fail-closed public verification entry point; AWS root pin is immutable.

    The calling Engine must atomically consume its challenge, validate actor,
    epoch, requested action and authorization, and enforce a protected decision.
    """
    root = Path(trusted_root_der_path).read_bytes()
    return _verify(
        document, root_der=root, root_digest=AWS_NITRO_ROOT_SHA256,
        expected_nonce=expected_nonce, expected_pcrs=expected_pcrs,
        expected_user_data=expected_user_data,
        expected_public_key=expected_public_key,
        now_ms=int(time.time() * 1000),
    )
