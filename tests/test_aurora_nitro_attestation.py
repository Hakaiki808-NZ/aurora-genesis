"""Synthetic PKI/COSE negative tests; NOT genuine AWS hardware attestation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

import cbor2
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.x509.oid import NameOID

from tools.aurora_nitro_attestation import (
    AttestationDenied, REQUIRED_PCRS, AWS_NITRO_ROOT_SHA256,
    _verify, verify_nitro_angel,
)


class NitroVerifierTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.now_ms = int(self.now.timestamp() * 1000)
        self.root_key = ec.generate_private_key(ec.SECP384R1())
        self.leaf_key = ec.generate_private_key(ec.SECP384R1())
        root_name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "synthetic-test-only-root"),
        ])
        leaf_name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "synthetic-test-only-leaf"),
        ])
        self.root = (
            x509.CertificateBuilder().subject_name(root_name)
            .issuer_name(root_name)
            .public_key(self.root_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1))
            .not_valid_after(self.now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .sign(self.root_key, hashes.SHA384())
        )
        self.leaf = (
            x509.CertificateBuilder().subject_name(leaf_name)
            .issuer_name(root_name)
            .public_key(self.leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1))
            .not_valid_after(self.now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(self.root_key, hashes.SHA384())
        )
        self.root_der = self.root.public_bytes(serialization.Encoding.DER)
        self.fake_root_digest = hashlib.sha256(self.root_der).hexdigest()
        self.nonce = os.urandom(32)
        self.user_data = os.urandom(32)
        self.public_key = os.urandom(48)
        self.pcrs = {k: hashlib.sha384(str(k).encode()).digest() for k in REQUIRED_PCRS}
        self.doc = self.make_document()

    def make_document(self, **changes) -> bytes:
        payload = {
            "module_id": "synthetic-test-module",
            "digest": "SHA384",
            "timestamp": self.now_ms,
            "nonce": self.nonce,
            "user_data": self.user_data,
            "public_key": self.public_key,
            "pcrs": dict(self.pcrs),
            "certificate": self.leaf.public_bytes(serialization.Encoding.DER),
            "cabundle": [],
        }
        payload.update(changes)
        protected = cbor2.dumps({1: -35})
        encoded = cbor2.dumps(payload)
        message = cbor2.dumps(["Signature1", protected, b"", encoded])
        sig_der = self.leaf_key.sign(message, ec.ECDSA(hashes.SHA384()))
        r, s = utils.decode_dss_signature(sig_der)
        sig = r.to_bytes(48, "big") + s.to_bytes(48, "big")
        return cbor2.dumps(cbor2.CBORTag(18, [protected, {}, encoded, sig]))

    def check(self, doc=None, **opts):
        args = {
            "document": doc if doc is not None else self.doc,
            "root_der": self.root_der,
            "root_digest": self.fake_root_digest,
            "expected_nonce": self.nonce,
            "expected_pcrs": self.pcrs,
            "expected_user_data": self.user_data,
            "expected_public_key": self.public_key,
            "now_ms": self.now_ms,
        }
        args.update(opts)
        return _verify(**args)

    def test_synthetic_sign1_with_chain_and_matching_pcrs(self):
        out = self.check()
        self.assertEqual(out.module_id, "synthetic-test-module")
        self.assertEqual(set(out.pcrs_hex), REQUIRED_PCRS)

    def test_root_fingerprint_mismatch(self):
        with self.assertRaisesRegex(AttestationDenied, "root"):
            self.check(root_digest="0" * 64)

    def test_real_public_entry_rejects_synthetic_root(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(self.root_der)
            file.flush()
            self.assertEqual(len(AWS_NITRO_ROOT_SHA256), 64)
            with self.assertRaisesRegex(AttestationDenied, "root"):
                verify_nitro_angel(
                    self.doc, trusted_root_der_path=file.name,
                    expected_nonce=self.nonce, expected_pcrs=self.pcrs,
                    expected_user_data=self.user_data,
                    expected_public_key=self.public_key,
                )

    def test_wrong_nonce_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "nonce"):
            self.check(expected_nonce=os.urandom(32))

    def test_missing_nonce_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "nonce"):
            self.check(self.make_document(nonce=None))

    def test_short_nonce_rejected(self):
        with self.assertRaises(AttestationDenied):
            self.check(expected_nonce=b"a")

    def test_modified_epoch_task_binding_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "binding"):
            self.check(expected_user_data=os.urandom(32))

    def test_different_enrolled_angel_key_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "Angel session key"):
            self.check(expected_public_key=os.urandom(48))

    def test_expired_timestamp_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "stale"):
            self.check(self.make_document(timestamp=self.now_ms - 150_000))

    def test_future_timestamp_rejected(self):
        with self.assertRaisesRegex(AttestationDenied, "stale"):
            self.check(self.make_document(timestamp=self.now_ms + 150_000))

    def test_changed_pcr_measurement_rejected(self):
        other = dict(self.pcrs)
        other[2] = hashlib.sha384(b"changed-enclave-image").digest()
        with self.assertRaisesRegex(AttestationDenied, "measurement"):
            self.check(expected_pcrs=other)

    def test_missing_signed_image_pcr8_rejected(self):
        other = dict(self.pcrs)
        del other[8]
        with self.assertRaisesRegex(AttestationDenied, "required"):
            self.check(expected_pcrs=other)

    def test_debug_zero_pcrs_rejected(self):
        zero = dict(self.pcrs)
        zero[0] = bytes(48)
        with self.assertRaisesRegex(AttestationDenied, "zero"):
            self.check(self.make_document(pcrs=zero))

    def test_corrupt_cose_signature_rejected(self):
        outer = cbor2.loads(self.doc)
        fields = list(outer.value)
        sig = bytearray(fields[-1])
        sig[-3] ^= 0x40
        fields[-1] = bytes(sig)
        with self.assertRaises(AttestationDenied):
            self.check(cbor2.dumps(cbor2.CBORTag(18, fields)))

    def test_trailing_bytes_rejected(self):
        with self.assertRaises(AttestationDenied):
            self.check(self.doc + b"garbage")

    def test_oversized_document_rejected(self):
        with self.assertRaises(AttestationDenied):
            self.check(b"x" * 20000)

    def test_forged_certificate_from_another_root_rejected(self):
        new_root = ec.generate_private_key(ec.SECP384R1())
        alt_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "different")])
        another = (
            x509.CertificateBuilder().subject_name(alt_name).issuer_name(alt_name)
            .public_key(new_root.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(self.now - timedelta(days=1))
            .not_valid_after(self.now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .sign(new_root, hashes.SHA384())
        )
        alt_der = another.public_bytes(serialization.Encoding.DER)
        with self.assertRaises(AttestationDenied):
            self.check(root_der=alt_der, root_digest=hashlib.sha256(alt_der).hexdigest())


if __name__ == "__main__":
    unittest.main()
