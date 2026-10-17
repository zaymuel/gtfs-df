"""
test_catalog.py - Unit tests for discover_catalog.py.
Completely offline using temporary files and mocks.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import config
import discover_catalog


class TestDiscoverCatalog(unittest.TestCase):
    def test_is_valid_df_urban_line(self):
        # Valid conventional lines
        self.assertTrue(discover_catalog.is_valid_df_urban_line("0.110"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("110.2"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("073.1"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("0.005"))

        # Valid BRT lines (Ticket 15)
        self.assertTrue(discover_catalog.is_valid_df_urban_line("2304"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("2201"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("3320"))
        self.assertTrue(discover_catalog.is_valid_df_urban_line("3201"))

        # Invalid lines (ANTT 8 digits, empty, non-digit chars)
        self.assertFalse(discover_catalog.is_valid_df_urban_line("12033870"))
        self.assertFalse(discover_catalog.is_valid_df_urban_line("1234567"))
        self.assertFalse(discover_catalog.is_valid_df_urban_line(""))
        self.assertFalse(discover_catalog.is_valid_df_urban_line(None))
        self.assertFalse(discover_catalog.is_valid_df_urban_line("0.110-A"))

    def test_clean_description(self):
        # Line number prefix removal
        desc1 = "0.110 0.110 Rodoviária do Plano Piloto / UNB"
        self.assertEqual(discover_catalog.clean_description(desc1, "0.110"), "Rodoviária do Plano Piloto / UNB")

        # Without dots in prefix
        desc2 = "0110 Rodoviária do Plano Piloto / UNB"
        self.assertEqual(discover_catalog.clean_description(desc2, "0.110"), "Rodoviária do Plano Piloto / UNB")

        # Empty description
        self.assertEqual(discover_catalog.clean_description("", "0.110"), "")
        self.assertEqual(discover_catalog.clean_description(None, "0.110"), "")

    @patch("bus2_client.fetch_routes")
    def test_run_discovery_offline(self, mock_fetch_routes):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            catalog_dir = tmppath / "catalog"
            bus2_dir = tmppath / "bus2"

            mock_routes = [
                {
                    "routeId": "kt6a",
                    "agencyId": "1",
                    "shortName": "0.110",
                    "longName": "0.110 Rodoviária do Plano Piloto / UNB",
                    "price": 2.70,
                    "color": "#449612"
                },
                {
                    "routeId": "antt_bad",
                    "agencyId": "9",
                    "shortName": "12033870",
                    "longName": "Linha Interestadual ANTT",
                    "price": 8.00,
                    "color": "#000000"
                },
                {
                    "routeId": "brt_3320",
                    "agencyId": "3",
                    "shortName": "3320",
                    "longName": "Terminal Santa Maria / Av. Alagados",
                    "price": 2.70,
                    "color": "#0072CE"
                }
            ]
            mock_fetch_routes.return_value = mock_routes

            # Patch config directories to avoid polluting production data
            with patch.object(config, "CATALOG_DIR", catalog_dir), \
                 patch.object(config, "BUS2_DIR", bus2_dir), \
                 patch.object(config, "CATALOG_PATH", catalog_dir / "lines.json"), \
                 patch.object(config, "BUS2_ROUTE_MAP_PATH", catalog_dir / "bus2_route_map.json"), \
                 patch.object(config, "BUS2_ROUTES_PATH", catalog_dir / "bus2_routes.json"), \
                 patch.object(config, "LEGACY_CATALOG_PATH", tmppath / "legacy_lines.json"):

                entries = discover_catalog.run_discovery()

                # Verify ANTT line was filtered out and BRT line was included
                line_numbers = [e["numero"] for e in entries]
                self.assertIn("0.110", line_numbers)
                self.assertIn("3320", line_numbers)
                self.assertNotIn("12033870", line_numbers)

                # Verify clean description
                entry_110 = next(e for e in entries if e["numero"] == "0.110")
                self.assertEqual(entry_110["descricao"], "Rodoviária do Plano Piloto / UNB")
                self.assertEqual(entry_110["tarifa"], 2.70)
                self.assertEqual(entry_110["cor"], "#449612")

                # Verify files were created
                self.assertTrue((catalog_dir / "lines.json").exists())
                self.assertTrue((catalog_dir / "bus2_route_map.json").exists())
                self.assertTrue((catalog_dir / "bus2_routes.json").exists())

    @patch("bus2_client.fetch_routes")
    def test_run_discovery_fallback_to_cache_and_legacy(self, mock_fetch_routes):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            catalog_dir = tmppath / "catalog"
            catalog_dir.mkdir(parents=True)
            bus2_dir = tmppath / "bus2"
            bus2_dir.mkdir(parents=True)

            # Bus2 API raises Exception
            mock_fetch_routes.side_effect = RuntimeError("Network down")

            # Local cache has 1 line in catalog_dir
            cached_file = catalog_dir / "bus2_routes.json"
            cached_file.write_text(json.dumps([{"shortName": "0.110", "longName": "Linha 0.110"}]), encoding="utf-8")

            # Legacy catalog has an additional line
            legacy_file = tmppath / "legacy_lines.json"
            legacy_file.write_text(json.dumps([{"numero": "2304", "descricao": "BRT Gama"}]), encoding="utf-8")

            with patch.object(config, "CATALOG_DIR", catalog_dir), \
                 patch.object(config, "BUS2_DIR", bus2_dir), \
                 patch.object(config, "CATALOG_PATH", catalog_dir / "lines.json"), \
                 patch.object(config, "BUS2_ROUTE_MAP_PATH", catalog_dir / "bus2_route_map.json"), \
                 patch.object(config, "BUS2_ROUTES_PATH", cached_file), \
                 patch.object(config, "LEGACY_CATALOG_PATH", legacy_file):

                entries = discover_catalog.run_discovery()
                numbers = [e["numero"] for e in entries]
                self.assertIn("0.110", numbers)
                self.assertIn("2304", numbers)


if __name__ == "__main__":
    unittest.main()

