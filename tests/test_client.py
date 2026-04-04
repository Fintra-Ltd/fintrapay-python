"""Tests for FintraPay Python SDK."""

import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import MagicMock, patch

from xfintrapay import FintraPay, verify_webhook_signature
from xfintrapay.client import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    FintraPayError,
)
from xfintrapay.models import CHAINS, TOKENS, TOKEN_CHAINS


class TestHMACSigning(unittest.TestCase):
    def setUp(self):
        self.client = FintraPay(
            api_key="xfp_key_test123",
            api_secret="xfp_secret_test456",
            base_url="https://api.example.com/v1",
        )

    def test_sign_produces_valid_headers(self):
        headers = self.client._sign("POST", "/invoices", '{"amount":"100"}')
        self.assertEqual(headers["X-API-Key"], "xfp_key_test123")
        self.assertIn("X-Timestamp", headers)
        self.assertIn("X-Signature", headers)
        self.assertEqual(len(headers["X-Signature"]), 64)  # SHA256 hex

    def test_sign_is_deterministic_for_same_timestamp(self):
        with patch("xfintrapay.client.time") as mock_time:
            mock_time.time.return_value = 1700000000
            h1 = self.client._sign("GET", "/invoices", "")
            h2 = self.client._sign("GET", "/invoices", "")
            self.assertEqual(h1["X-Signature"], h2["X-Signature"])

    def test_sign_differs_for_different_body(self):
        with patch("xfintrapay.client.time") as mock_time:
            mock_time.time.return_value = 1700000000
            h1 = self.client._sign("POST", "/invoices", '{"a":1}')
            h2 = self.client._sign("POST", "/invoices", '{"b":2}')
            self.assertNotEqual(h1["X-Signature"], h2["X-Signature"])

    def test_signature_matches_manual_computation(self):
        with patch("xfintrapay.client.time") as mock_time:
            mock_time.time.return_value = 1711054800
            headers = self.client._sign("POST", "/invoices", '{"amount":"100"}')
            payload = '1711054800\nPOST\n/invoices\n{"amount":"100"}'
            expected = hmac.new(
                b"xfp_secret_test456", payload.encode(), hashlib.sha256
            ).hexdigest()
            self.assertEqual(headers["X-Signature"], expected)


class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        self.client = FintraPay(api_key="k", api_secret="s")

    def _mock_response(self, status, data, headers=None):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = 200 <= status < 300
        resp.json.return_value = data
        resp.headers = headers or {}
        resp.text = json.dumps(data)
        return resp

    @patch("xfintrapay.client.requests.Session.request")
    def test_authentication_error(self, mock_req):
        mock_req.return_value = self._mock_response(401, {"error": "invalid", "code": "AUTH"})
        with self.assertRaises(AuthenticationError) as ctx:
            self.client.get_invoice("abc")
        self.assertEqual(ctx.exception.status, 401)

    @patch("xfintrapay.client.requests.Session.request")
    def test_validation_error(self, mock_req):
        mock_req.return_value = self._mock_response(422, {
            "error": "Validation failed", "code": "VALIDATION_ERROR",
            "details": {"amount": "required"},
        })
        with self.assertRaises(ValidationError) as ctx:
            self.client.create_invoice(amount="")
        self.assertEqual(ctx.exception.details["amount"], "required")

    @patch("xfintrapay.client.requests.Session.request")
    def test_rate_limit_error(self, mock_req):
        mock_req.return_value = self._mock_response(
            429, {"error": "rate limit"}, headers={"Retry-After": "30"}
        )
        with self.assertRaises(RateLimitError) as ctx:
            self.client.list_invoices()
        self.assertEqual(ctx.exception.retry_after, 30)

    @patch("xfintrapay.client.requests.Session.request")
    def test_success_returns_data(self, mock_req):
        mock_req.return_value = self._mock_response(200, {"id": "inv_123", "status": "pending"})
        result = self.client.get_invoice("inv_123")
        self.assertEqual(result["id"], "inv_123")


class TestWebhookVerification(unittest.TestCase):
    def test_valid_signature(self):
        secret = "webhook_secret_abc"
        body = b'{"event":"payment.received","invoice_id":"123"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(body, sig, secret))

    def test_invalid_signature(self):
        self.assertFalse(verify_webhook_signature(b"body", "wrong", "secret"))

    def test_empty_inputs(self):
        self.assertFalse(verify_webhook_signature(b"", "", ""))
        self.assertFalse(verify_webhook_signature(None, "sig", "secret"))

    def test_string_body(self):
        secret = "s"
        body = '{"test":true}'
        sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(body, sig, secret))


class TestModels(unittest.TestCase):
    def test_all_chains_present(self):
        self.assertEqual(len(CHAINS), 7)
        self.assertIn("tron", CHAINS)
        self.assertIn("solana", CHAINS)

    def test_all_tokens_present(self):
        self.assertEqual(len(TOKENS), 6)
        self.assertIn("USDT", TOKENS)

    def test_usdc_not_on_tron(self):
        self.assertNotIn("tron", TOKEN_CHAINS["USDC"])

    def test_usdt_on_all_chains(self):
        self.assertEqual(len(TOKEN_CHAINS["USDT"]), 7)


class TestClientInit(unittest.TestCase):
    def test_requires_credentials(self):
        with self.assertRaises(ValueError):
            FintraPay(api_key="", api_secret="")

    def test_custom_base_url(self):
        c = FintraPay(api_key="k", api_secret="s", base_url="http://localhost:8080/v1/")
        self.assertEqual(c.base_url, "http://localhost:8080/v1")


if __name__ == "__main__":
    unittest.main()
