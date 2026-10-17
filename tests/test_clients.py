"""
test_clients.py - Unit tests for http_client.py and bus2_client.py.
Completely offline using unittest.mock.
"""

import base64
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config
import http_client
from http_client import HttpRequestError, PoliteClient
import bus2_client


class TestHttpClient(unittest.TestCase):
    def setUp(self):
        self.client = PoliteClient(
            base_url="https://api.test.df.gov.br",
            delay=0.001,
            retries=3,
            backoff=0.01,
            timeout=5
        )

    @patch("requests.Session.get")
    def test_get_json_success_absolute_and_relative(self, mock_get):
        # Test 200 OK
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok", "items": [1, 2, 3]}
        mock_get.return_value = mock_resp

        # Relative path
        res1 = self.client.get_json("/endpoint/test")
        self.assertEqual(res1, {"status": "ok", "items": [1, 2, 3]})
        mock_get.assert_called_with("https://api.test.df.gov.br/endpoint/test", params=None, timeout=5)

        # Absolute URL
        res2 = self.client.get_json("https://external.test/data")
        self.assertEqual(res2, {"status": "ok", "items": [1, 2, 3]})
        mock_get.assert_called_with("https://external.test/data", params=None, timeout=5)

        self.assertEqual(self.client.request_count, 2)
        self.assertEqual(self.client.retry_count, 0)

    @patch("requests.Session.get")
    def test_get_response_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html>Portal Content</html>"
        mock_resp.url = "https://dfnoponto.semob.df.gov.br/"
        mock_get.return_value = mock_resp

        resp = self.client.get_response("https://dfnoponto.semob.df.gov.br/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, "<html>Portal Content</html>")
        self.assertEqual(str(resp.url), "https://dfnoponto.semob.df.gov.br/")

    @patch("requests.Session.get")
    def test_get_json_404_and_204_returns_none(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        res_404 = self.client.get_json("/not-found")
        self.assertIsNone(res_404)

        mock_resp.status_code = 204
        res_204 = self.client.get_json("/no-content")
        self.assertIsNone(res_204)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_get_json_retry_on_500_and_succeed(self, mock_get, mock_sleep):
        # 1st attempt: 500 error; 2nd attempt: 200 OK
        resp_500 = MagicMock()
        resp_500.status_code = 500
        resp_500.headers = {}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"recovered": True}

        mock_get.side_effect = [resp_500, resp_200]

        res = self.client.get_json("/flaky-endpoint")
        self.assertEqual(res, {"recovered": True})
        self.assertEqual(self.client.request_count, 2)
        self.assertEqual(self.client.retry_count, 1)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_get_json_retry_after_header_handling(self, mock_get, mock_sleep):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "2.5"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"success": True}

        mock_get.side_effect = [resp_429, resp_200]

        res = self.client.get_json("/rate-limited")
        self.assertEqual(res, {"success": True})
        self.assertEqual(self.client.retry_count, 1)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_get_json_persistent_error_raises_exception(self, mock_get, mock_sleep):
        resp_503 = MagicMock()
        resp_503.status_code = 503
        resp_503.headers = {}
        mock_get.return_value = resp_503

        with self.assertRaises(HttpRequestError):
            self.client.get_json("/broken")

        self.assertEqual(self.client.request_count, 3)

    @patch("time.sleep", return_value=None)
    @patch("requests.Session.get")
    def test_get_json_network_exception_handling(self, mock_get, mock_sleep):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with self.assertRaises(HttpRequestError):
            self.client.get_json("/timeout")

        self.assertEqual(self.client.request_count, 3)
        self.assertEqual(self.client.retry_count, 3)


class TestBus2Client(unittest.TestCase):
    def test_base36_encode_and_decode(self):
        # Test standard conversion
        self.assertEqual(bus2_client.base36_encode(970930), "kt6a")
        self.assertEqual(bus2_client.base36_decode("kt6a"), 970930)

        # Test project hash 5600313 -> 3c189
        self.assertEqual(bus2_client.base36_encode(5600313), "3c189")
        self.assertEqual(bus2_client.base36_decode("3c189"), 5600313)

        # Zero edge case
        self.assertEqual(bus2_client.base36_encode(0), "0")
        self.assertEqual(bus2_client.base36_decode("0"), 0)

    def test_evp_bytes_to_key(self):
        passphrase = b"test_passphrase"
        salt = b"12345678"
        key, iv = bus2_client._evp_bytes_to_key(passphrase, salt, key_len=32, iv_len=16)
        self.assertEqual(len(key), 32)
        self.assertEqual(len(iv), 16)
        # Deterministic check
        key2, iv2 = bus2_client._evp_bytes_to_key(passphrase, salt, key_len=32, iv_len=16)
        self.assertEqual(key, key2)
        self.assertEqual(iv, iv2)

    def test_decrypt_payload_roundtrip(self):
        # Create an encrypted OpenSSL payload compatible with CryptoJS
        sample_data = {"routeId": "kt6a", "name": "Linha 0.110", "trips": [1, 2, 3]}
        passphrase = "my_secret_passphrase"

        salt = os.urandom(8)
        key, iv = bus2_client._evp_bytes_to_key(passphrase.encode("utf-8"), salt, 32, 16)
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        padder = padding.PKCS7(128).padder()
        padded = padder.update(json.dumps(sample_data).encode("utf-8")) + padder.finalize()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        raw = b"Salted__" + salt + ciphertext
        token = base64.b64encode(raw).decode("utf-8")

        decrypted = bus2_client.decrypt_payload(token, passphrase=passphrase)
        self.assertEqual(decrypted, sample_data)

    def test_decrypt_payload_invalid_format(self):
        invalid_raw = b"NotSalted" + os.urandom(24)
        token = base64.b64encode(invalid_raw).decode("utf-8")
        with self.assertRaises(ValueError):
            bus2_client.decrypt_payload(token)

    @patch("requests.Session.get")
    def test_get_json_with_encrypted_payload(self, mock_get):
        sample_dict = {"stops": ["P1", "P2"]}
        passphrase = config.BUS2_ENCRYPTION_KEY
        salt = os.urandom(8)
        key, iv = bus2_client._evp_bytes_to_key(passphrase.encode("utf-8"), salt, 32, 16)
        encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
        padder = padding.PKCS7(128).padder()
        padded = padder.update(json.dumps(sample_dict).encode("utf-8")) + padder.finalize()
        ciphertext = encryptor.update(padded) + encryptor.finalize()
        raw = b"Salted__" + salt + ciphertext
        token = base64.b64encode(raw).decode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": token}
        mock_get.return_value = mock_resp

        session = requests.Session()
        res = bus2_client._get_json("https://painel.mobilibus.com/v2/api/public/get-trips/", session=session)
        self.assertEqual(res, sample_dict)

    @patch("bus2_client._get_json")
    def test_public_fetch_wrappers(self, mock_get_json):
        mock_get_json.return_value = [{"shortName": "0.110"}]
        routes = bus2_client.fetch_routes()
        self.assertEqual(routes, [{"shortName": "0.110"}])

        mock_get_json.return_value = [{"agencyId": "1"}]
        agencies = bus2_client.fetch_agencies()
        self.assertEqual(agencies, [{"agencyId": "1"}])

        mock_get_json.return_value = {"trips": []}
        trips = bus2_client.fetch_trips("0.110")
        self.assertEqual(trips, {"trips": []})

        mock_get_json.return_value = {"template": "details"}
        tpl = bus2_client.fetch_trip_template("1234")
        self.assertEqual(tpl, {"template": "details"})

        mock_get_json.return_value = {"timetable": {}}
        tt = bus2_client.fetch_timetable("kt6a")
        self.assertEqual(tt, {"timetable": {}})

        mock_get_json.return_value = {"points": []}
        td = bus2_client.fetch_trip_details("trip_123")
        self.assertEqual(td, {"points": []})

    @patch("time.sleep", return_value=None)
    @patch("requests.get")
    def test_get_json_plain_json_and_error_handling(self, mock_get, mock_sleep):
        # 1. Plain 200 JSON
        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"routes": [{"id": 1}]}
        mock_get.return_value = resp_200

        res1 = bus2_client._get_json("https://mobilibus.com/api/routes")
        self.assertEqual(res1, {"routes": [{"id": 1}]})

        # 2. 404 Not Found -> None
        resp_404 = MagicMock()
        resp_404.status_code = 404
        mock_get.return_value = resp_404
        res_404 = bus2_client._get_json("https://mobilibus.com/api/missing")
        self.assertIsNone(res_404)

        # 3. 500 Retry and recovery
        resp_500 = MagicMock()
        resp_500.status_code = 500
        mock_get.side_effect = [resp_500, resp_200]
        res_retry = bus2_client._get_json("https://mobilibus.com/api/flaky", retries=2, backoff=0.01)
        self.assertEqual(res_retry, {"routes": [{"id": 1}]})

        # 4. RequestException exhausted -> None
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection lost")
        res_err = bus2_client._get_json("https://mobilibus.com/api/down", retries=2, backoff=0.01)
        self.assertIsNone(res_err)


if __name__ == "__main__":
    unittest.main()

