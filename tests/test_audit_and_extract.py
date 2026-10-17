"""
test_audit_and_extract.py - Unit tests for audit_dfnoponto.py, extract.py, and harvest_dftrans.py.
Completely offline using mocks and temporary fixtures.
"""

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config
import audit_dfnoponto
import extract
from http_client import PoliteClient, HttpRequestError


class TestExtract(unittest.TestCase):
    def test_load_catalog_formats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "catalog.json"

            # Format 1: List of dicts with active flag
            data1 = [
                {"numero": "0.110", "ativo": True},
                {"numero": "2304", "ativo": True},
                {"numero": "999.9", "ativo": False},
            ]
            p.write_text(json.dumps(data1), encoding="utf-8")
            lines1 = extract.load_catalog(p)
            self.assertEqual(lines1, ["0.110", "2304"])

            # Format 2: List of strings
            data2 = ["110.2", "0.110", "110.2"]  # with duplicate
            p.write_text(json.dumps(data2), encoding="utf-8")
            lines2 = extract.load_catalog(p)
            self.assertEqual(lines2, ["0.110", "110.2"])

            # Format 3: Dict mapping
            data3 = {"0.110": {"numero": "0.110"}, "2201": {}}
            p.write_text(json.dumps(data3), encoding="utf-8")
            lines3 = extract.load_catalog(p)
            self.assertEqual(lines3, ["0.110", "2201"])

    def test_ensure_master_stops_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_stops = Path(tmpdir) / "all_stops.geojson"
            fake_stops.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
            client = MagicMock(spec=PoliteClient)

            with patch.object(config, "STOPS_MASTER_PATH", fake_stops):
                res = extract.ensure_master_stops(client, force=False)
                self.assertEqual(res, fake_stops)
                client.get_json.assert_not_called()

    def test_ensure_master_stops_download(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_stops = Path(tmpdir) / "all_stops.geojson"
            client = MagicMock(spec=PoliteClient)
            client.get_json.return_value = {"type": "FeatureCollection", "features": [{"id": 1}]}

            with patch.object(config, "STOPS_MASTER_PATH", fake_stops):
                res = extract.ensure_master_stops(client, force=True)
                self.assertEqual(res, fake_stops)
                self.assertTrue(fake_stops.exists())
                data = json.loads(fake_stops.read_text(encoding="utf-8"))
                self.assertEqual(len(data["features"]), 1)

    def test_fetch_line_dftrans_and_percursos(self):
        client = MagicMock(spec=PoliteClient)

        # Line meta list response
        client.get_json.side_effect = [
            [{"sequencial": 101, "numero": "0.110"}],  # fetch_line_dftrans
            {"features": [{"geometry": {"coordinates": [[0, 0]]}}]},  # fetch_percursos
            {"diasUteis": ["06:00", "07:00"]}  # fetch_horarios
        ]

        meta = extract.fetch_line_dftrans(client, "0.110")
        self.assertEqual(meta, {"sequencial": 101, "numero": "0.110"})

        percursos = extract.fetch_percursos(client, "0.110", meta)
        self.assertIn("numero", percursos)

        horarios = extract.fetch_horarios(client, "0.110", meta)
        self.assertIn("numero", horarios)

    def test_fetch_bus2_supplement(self):
        bus2_map = {"0.110": {"routeId": "kt6a"}}

        with patch("bus2_client.fetch_timetable") as mock_tt, \
             patch("bus2_client.fetch_trip_details") as mock_td:
            mock_tt.return_value = {
                "timetable": {"trips": [{"tripId": "trip_abc"}]}
            }
            mock_td.return_value = {"points": [1, 2]}

            supp = extract.fetch_bus2_supplement("0.110", bus2_map)
            self.assertIn("timetable", supp)
            self.assertIn("trip_details", supp)

    def test_process_line_worker_cache_hit_and_atomic_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()

            lock = threading.Lock()
            stats = {"saved": 0, "skipped": 0, "failed": 0}
            client = MagicMock(spec=PoliteClient)

            with patch.object(config, "RAW_DIR", raw_dir):
                # 1. First run: extracts and saves atomically
                client.get_json.side_effect = [
                    [{"sequencial": 101}],  # meta
                    {"features": [{"id": 1}]},  # percurso
                    {"partidas": ["06:00"]}  # horario
                ]
                status = extract.process_line_worker("0.110", client, force=False, bus2_map=None, lock=lock, stats=stats)
                self.assertIn("OK 0.110", status)
                self.assertEqual(stats["saved"], 1)
                self.assertTrue((raw_dir / "0.110.json").exists())

                # 2. Second run without force: cache hit
                status_cache = extract.process_line_worker("0.110", client, force=False, bus2_map=None, lock=lock, stats=stats)
                self.assertEqual(status_cache, "CACHE 0.110")
                self.assertEqual(stats["skipped"], 1)


    def test_extract_catalog_fallbacks_and_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            missing_cat = tmppath / "missing.json"
            legacy_cat = tmppath / "legacy.json"

            # 1. Fallback to legacy
            legacy_cat.write_text(json.dumps([{"numero": "0.110"}]), encoding="utf-8")
            with patch.object(config, "LEGACY_CATALOG_PATH", legacy_cat):
                lines = extract.load_catalog(missing_cat)
                self.assertEqual(lines, ["0.110"])

            # 2. Both missing -> FileNotFoundError
            with patch.object(config, "LEGACY_CATALOG_PATH", tmppath / "not_there.json"):
                with self.assertRaises(FileNotFoundError):
                    extract.load_catalog(missing_cat)

    def test_fetch_percursos_and_horarios_sequencial_fallbacks(self):
        client = MagicMock(spec=PoliteClient)
        # Percurso: number returns None, seq returns features
        client.get_json.side_effect = [
            None,  # percurso by number
            {"features": [{"properties": {}, "geometry": {"coordinates": [[0, 0]]}}]},  # percurso by seq
            None,  # horario by number
            [{"horario": "07:30"}]  # horario by seq
        ]
        meta = {"sequencial": 999}
        percursos = extract.fetch_percursos(client, "0.110", meta)
        self.assertIn("999", percursos)

        horarios = extract.fetch_horarios(client, "0.110", meta)
        self.assertIn("999", horarios)

    def test_process_line_worker_no_data_and_write_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir()
            lock = threading.Lock()
            stats = {"saved": 0, "skipped": 0, "failed": 0}
            client = MagicMock(spec=PoliteClient)

            with patch.object(config, "RAW_DIR", raw_dir):
                # 1. No meta and no percursos -> SEM_DADOS
                client.get_json.return_value = None
                res_no_data = extract.process_line_worker("999.9", client, force=False, bus2_map=None, lock=lock, stats=stats)
                self.assertIn("SEM_DADOS", res_no_data)
                self.assertEqual(stats["failed"], 1)

                # 2. Write exception -> ERRO
                client.get_json.side_effect = [
                    [{"sequencial": 101}],
                    {"features": [{"id": 1}]},
                    {"partidas": ["06:00"]}
                ]
                with patch("json.dump", side_effect=OSError("Disk full")):
                    res_err = extract.process_line_worker("0.110", client, force=False, bus2_map=None, lock=lock, stats=stats)
                    self.assertIn("ERRO", res_err)
                    self.assertEqual(stats["failed"], 2)

    def test_extract_main_cli(self):
        with patch("sys.argv", ["extract.py", "--lines", "0.110", "--workers", "1", "--limit", "1"]), \
             patch("extract.ensure_master_stops") as mock_stops, \
             patch("extract.process_line_worker", return_value="OK 0.110"):
            mock_stops.return_value = Path("all_stops.geojson")
            extract.main()
            mock_stops.assert_called_once()



class TestAuditDfNoPonto(unittest.TestCase):
    def test_audit_offline_htmls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            html_dir = Path(tmpdir) / "htmls"
            html_dir.mkdir()

            sample_html = """
            <html>
                <body>
                    <iframe src="https://bus2.info/reports/2you/3c189"></iframe>
                    <div class="linha-numero">0.110</div>
                    <div class="linha-numero">2304</div>
                </body>
            </html>
            """
            (html_dir / "test_portal.html").write_text(sample_html, encoding="utf-8")

            with patch.object(audit_dfnoponto, "HTMLS_DIR", html_dir):
                catalog_lines = {"0.110", "2304", "0.108"}
                res = audit_dfnoponto.audit_offline_htmls(catalog_lines)
                self.assertIn("test_portal.html", res)
                self.assertEqual(res["test_portal.html"], {"0.110", "2304"})

    def test_audit_live_endpoints(self):
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://dfnoponto.semob.df.gov.br/"
        mock_resp.text = '<html>Linha 0.110 e Linha 2304 <iframe src="test"></iframe></html>'
        mock_client.get_response.return_value = mock_resp

        catalog_lines = {"0.110", "2304"}
        results = audit_dfnoponto.audit_live_endpoints(catalog_lines, client=mock_client)
        self.assertIn("dfnoponto_com_br", results)
        self.assertEqual(results["dfnoponto_com_br"]["status"], 200)
        self.assertEqual(results["dfnoponto_com_br"]["recognized_lines"], 2)

        # Test HttpRequestError handling
        mock_client.get_response.side_effect = HttpRequestError("Timeout after 3 retries")
        err_results = audit_dfnoponto.audit_live_endpoints(catalog_lines, client=mock_client)
        self.assertIn("error", err_results["dfnoponto_com_br"])
        self.assertIn("Timeout after 3 retries", err_results["dfnoponto_com_br"]["error"])

        # Test unexpected exception handling
        mock_client.get_response.side_effect = ValueError("Unexpected parsing issue")
        unexpected_results = audit_dfnoponto.audit_live_endpoints(catalog_lines, client=mock_client)
        self.assertIn("error", unexpected_results["dfnoponto_com_br"])
        self.assertIn("Unexpected parsing issue", unexpected_results["dfnoponto_com_br"]["error"])

    def test_audit_main_flow(self):
        with patch.object(audit_dfnoponto, "audit_offline_htmls", return_value={"Todas as linhas.html": {"0.110", "12033870"}}), \
             patch.object(audit_dfnoponto, "audit_live_endpoints", return_value={}):
            # Runs main without throwing
            audit_dfnoponto.main()


if __name__ == "__main__":
    unittest.main()

