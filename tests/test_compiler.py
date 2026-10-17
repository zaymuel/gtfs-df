"""
Test suite for Tickets 04, 05, 14, 15: GTFS compiler, Shapely linear referencing,
fare modeling, basin color schemes, and BRT subsystem processing.
"""

import csv
import json
import sys
import unittest
import zipfile
from pathlib import Path
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree

# Add project root and scripts to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_gtfs
import config


class TestGtfsCompiler(unittest.TestCase):
    def test_crs_conversion(self):
        # Test Web Mercator to WGS84 reprojection for Rodoviária do Plano Piloto (~ -47.882, -15.794)
        x_3857 = -5330200.0
        y_3857 = -1780000.0
        lon, lat = build_gtfs.to_wgs84(x_3857, y_3857)
        self.assertTrue(build_gtfs.is_in_bbox(lat, lon))
        self.assertAlmostEqual(lat, -15.79, delta=0.2)
        self.assertAlmostEqual(lon, -47.88, delta=0.2)

    def test_time_formatting_post_midnight(self):
        # 23:45:00
        sec_2345 = 23 * 3600 + 45 * 60
        self.assertEqual(build_gtfs.format_gtfs_time(sec_2345), "23:45:00")

        # 24:15:00 (Next day / post-midnight GTFS spec)
        sec_2415 = 24 * 3600 + 15 * 60
        self.assertEqual(build_gtfs.format_gtfs_time(sec_2415), "24:15:00")

        # 25:30:00
        sec_2530 = 25 * 3600 + 30 * 60
        self.assertEqual(build_gtfs.format_gtfs_time(sec_2530), "25:30:00")

    def test_parse_time_to_seconds(self):
        self.assertEqual(build_gtfs.parse_time_to_seconds("05:55"), 5 * 3600 + 55 * 60)
        self.assertEqual(build_gtfs.parse_time_to_seconds("24:10:00"), 24 * 3600 + 10 * 60)
        self.assertIsNone(build_gtfs.parse_time_to_seconds(None))

    def test_brt_subsystem_classification(self):
        # Ticket 15: BRT Troncais (21xx, 22xx, 23xx, 24xx) vs BRT Alimentadoras (32xx, 33xx)
        compiler = build_gtfs.GtfsCompiler()

        # Troncais BRT (40 km/h)
        speed, is_trunk = compiler.get_line_speed("2304", [])
        self.assertTrue(is_trunk)
        self.assertEqual(speed, config.SPEED_BRT_KMH)

        speed, is_trunk = compiler.get_line_speed("2201", [])
        self.assertTrue(is_trunk)
        self.assertEqual(speed, config.SPEED_BRT_KMH)

        # Alimentadora BRT sem ponto (3320: Av. Alagados / Terminal BRT Santa Maria)
        self.assertTrue(config.is_brt_feeder("3320"))
        speed, is_trunk = compiler.get_line_speed("3320", [])
        self.assertFalse(is_trunk)
        self.assertEqual(speed, config.SPEED_CONVENTIONAL_KMH)

        # Linha convencional (0.110)
        self.assertFalse(config.is_brt_feeder("0.110"))
        speed, is_trunk = compiler.get_line_speed("0.110", [])
        self.assertFalse(is_trunk)
        self.assertEqual(speed, config.SPEED_CONVENTIONAL_KMH)

    def test_route_colors_and_contrast(self):
        # Ticket 14: Visual identity colors from catalog
        compiler = build_gtfs.GtfsCompiler()

        # Bacia 5 (BsBus, #bbff00 -> fundo claro, texto preto 000000)
        compiler.catalog_map["0.005"] = {"cor": "#bbff00"}
        color, text = compiler.get_route_colors("0.005", is_brt=False)
        self.assertEqual(color, "BBFF00")
        self.assertEqual(text, "000000")

        # Bacia 1 (Piracicabana, #449612 -> fundo escuro, texto branco FFFFFF)
        compiler.catalog_map["0.006"] = {"cor": "#449612"}
        color, text = compiler.get_route_colors("0.006", is_brt=False)
        self.assertEqual(color, "449612")
        self.assertEqual(text, "FFFFFF")

    def test_compile_sample_lines_and_fares(self):
        # Tickets 04 & 05: Compilação GTFS e modelagem de tarifas
        compiler = build_gtfs.GtfsCompiler()
        compiler.compile_all()

        gtfs_dir = config.GTFS_DIR
        self.assertTrue((gtfs_dir / "agency.txt").exists())
        self.assertTrue((gtfs_dir / "routes.txt").exists())
        self.assertTrue((gtfs_dir / "calendar.txt").exists())
        self.assertTrue((gtfs_dir / "shapes.txt").exists())
        self.assertTrue((gtfs_dir / "fare_attributes.txt").exists())
        self.assertTrue((gtfs_dir / "fare_rules.txt").exists())
        self.assertTrue((gtfs_dir / "gtfs_df.zip").exists())

        # Verifica conteúdo do zip
        with zipfile.ZipFile(gtfs_dir / "gtfs_df.zip", "r") as zf:
            zip_names = zf.namelist()
            self.assertIn("fare_attributes.txt", zip_names)
            self.assertIn("fare_rules.txt", zip_names)
            self.assertIn("routes.txt", zip_names)
            self.assertIn("shapes.txt", zip_names)

        # Verifica se tarifas têm currency_type=BRL
        with open(gtfs_dir / "fare_attributes.txt", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fares = list(reader)
            if fares:
                for fare in fares:
                    self.assertEqual(fare["currency_type"], "BRL")
                    self.assertTrue(float(fare["price"]) > 0)

    def test_build_stops_index_and_out_of_bounds_logging(self):
        import tempfile
        import json
        from shapely.geometry import Point
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            master_file = tmppath / "all_stops.geojson"
            catalog_dir = tmppath / "catalog"
            catalog_dir.mkdir()

            geojson_data = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-5330200.0, -1780000.0]},
                        "properties": {"sequencial": 1001, "descricao": "Parada Rodoviária"}
                    },
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-5330500.0, -1780200.0]},
                        "properties": {"sequencial": 1002, "logradouro": "Parada W3 Sul"}
                    },
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                        "properties": {"sequencial": 9999, "descricao": "Parada Oceano"}
                    }
                ]
            }
            master_file.write_text(json.dumps(geojson_data), encoding="utf-8")

            with patch.object(config, "STOPS_MASTER_PATH", master_file), \
                 patch.object(config, "CATALOG_DIR", catalog_dir):
                stops = build_gtfs.load_master_stops()
                # Should have 2 valid stops, 1 out of bounds
                self.assertEqual(len(stops), 2)
                self.assertIn("1001", stops)
                self.assertIn("1002", stops)
                self.assertNotIn("9999", stops)

                # Out of bounds logging
                out_bounds_file = catalog_dir / "out_of_bounds_stops.json"
                self.assertTrue(out_bounds_file.exists())
                logged = json.loads(out_bounds_file.read_text(encoding="utf-8"))
                self.assertEqual(len(logged), 1)
                self.assertEqual(logged[0]["stop_id"], "9999")

    def test_route_colors_fallback_and_invalid(self):
        compiler = build_gtfs.GtfsCompiler()

        # Fallback BRT (no entry in catalog)
        c_brt, t_brt = compiler.get_route_colors("9999", is_brt=True)
        self.assertEqual(c_brt, "E60000")
        self.assertEqual(t_brt, "FFFFFF")

        # Fallback conventional (no entry in catalog)
        c_conv, t_conv = compiler.get_route_colors("9999", is_brt=False)
        self.assertEqual(c_conv, "175898")
        self.assertEqual(t_conv, "FFFFFF")

        # Invalid hex string
        compiler.catalog_map["bad_hex"] = {"cor": "INVALID"}
        c_bad, t_bad = compiler.get_route_colors("bad_hex", is_brt=False)
        self.assertEqual(c_bad, "175898")

    def test_process_raw_line_generates_trips_and_stoptimes(self):
        import tempfile
        from shapely.strtree import STRtree

        compiler = build_gtfs.GtfsCompiler()
        p1 = Point(-5330200.0, -1780000.0)
        p2 = Point(-5330800.0, -1780000.0)
        compiler.master_stops = {
            "1001": {"stop_id": "1001", "x_3857": p1.x, "y_3857": p1.y, "stop_name": "P1", "stop_lat": -15.79, "stop_lon": -47.88},
            "1002": {"stop_id": "1002", "x_3857": p2.x, "y_3857": p2.y, "stop_name": "P2", "stop_lat": -15.80, "stop_lon": -47.89}
        }
        compiler.stop_points = [p1, p2]
        compiler.stop_keys = ["1001", "1002"]
        compiler.str_tree = STRtree(compiler.stop_points)

        with tempfile.TemporaryDirectory() as tmpdir:
            raw_path = Path(tmpdir) / "0.110.json"
            raw_data = {
                "numero": "0.110",
                "linha": {
                    "descricao": "Rodoviária / UNB",
                    "faixaTarifaria": "2.70"
                },
                "percursos": {
                    "ida": {
                        "features": [
                            {
                                "properties": {"sentido": "IDA"},
                                "geometry": {
                                    "type": "LineString",
                                    "coordinates": [
                                        [-5330000.0, -1780000.0],
                                        [-5331000.0, -1780000.0]
                                    ]
                                }
                            }
                        ]
                    }
                },
                "horarios": {
                    "ida": [
                        {"dias": "SEG_SEX", "hora": "06:00"},
                        {"dias": "SEG_SEX", "hora": "06:30"}
                    ]
                }
            }
            raw_path.write_text(json.dumps(raw_data), encoding="utf-8")

            compiler.process_raw_line(raw_path)

            # Check that route, trips, stops, and stop_times were populated
            self.assertEqual(len(compiler.routes), 1)
            self.assertEqual(compiler.routes[0]["route_id"], "R_0.110")
            self.assertEqual(len(compiler.trips), 2)
            self.assertTrue(len(compiler.stop_times) >= 4)  # 2 trips * 2 stops
            self.assertIn("1001", compiler.stops)
            self.assertIn("1002", compiler.stops)

    def test_snap_stops_along_line_bus2_and_strtree(self):
        from shapely.geometry import LineString, Point
        from shapely.strtree import STRtree

        compiler = build_gtfs.GtfsCompiler()
        line_geom = LineString([(-5330000.0, -1780000.0), (-5332000.0, -1780000.0)])

        # 1. Bus2 stops
        bus2_data = {
            "trip_details": {
                "stops": [
                    {"stopId": "S1", "lat": -15.794, "lng": -47.882, "name": "P1"},
                    {"stopId": "S2", "lat": -15.795, "lng": -47.885, "name": "P2"}
                ]
            }
        }
        snapped_b2 = compiler.snap_stops_along_line(line_geom, bus2_data, "IDA")
        self.assertEqual(len(snapped_b2), 2)
        self.assertTrue(snapped_b2[0][1] < snapped_b2[1][1])

        # 2. STRtree fallback
        stop_p1 = Point(-5330500.0, -1780005.0)  # 5m off centerline (within 35m corridor)
        stop_p2 = Point(-5331500.0, -1780010.0)  # 10m off centerline
        compiler.master_stops = {
            "101": {"stop_id": "101", "x_3857": stop_p1.x, "y_3857": stop_p1.y, "stop_name": "Parada 101"},
            "102": {"stop_id": "102", "x_3857": stop_p2.x, "y_3857": stop_p2.y, "stop_name": "Parada 102"}
        }
        compiler.stop_points = [stop_p1, stop_p2]
        compiler.stop_keys = ["101", "102"]
        compiler.str_tree = STRtree(compiler.stop_points)

        snapped_tree = compiler.snap_stops_along_line(line_geom, {}, "IDA")
        self.assertEqual(len(snapped_tree), 2)
        self.assertEqual(snapped_tree[0][0]["stop_id"], "101")
        self.assertEqual(snapped_tree[1][0]["stop_id"], "102")

    def test_extract_departures(self):
        compiler = build_gtfs.GtfsCompiler()

        # Bus2 timetable format
        bus2_data = {
            "timetable": {
                "directions": [
                    {
                        "services": [
                            {"desc": "Dias Úteis", "departures": [{"dep": "06:00"}, {"dep": "06:30"}]},
                            {"desc": "Sábados", "departures": [{"dep": "07:00"}]},
                            {"desc": "Domingos e Feriados", "departures": [{"dep": "08:00"}]}
                        ]
                    }
                ]
            }
        }
        deps_b2 = compiler.extract_departures({}, bus2_data, "IDA")
        self.assertEqual(deps_b2["SEG_SEX"], ["06:00", "06:30"])
        self.assertEqual(deps_b2["SABADO"], ["07:00"])
        self.assertEqual(deps_b2["DOM_FER"], ["08:00"])

        # DFTrans schedule fallback format
        dftrans_horarios = {
            "ida": [
                {"dias": "SEG_SEX", "horario": "05:30"},
                {"tipoDia": "SAB", "hora": "06:15"},
                {"tipoDia": "DOM", "hora": "07:15"}
            ]
        }
        deps_df = compiler.extract_departures(dftrans_horarios, {}, "IDA")
        self.assertEqual(deps_df["SEG_SEX"], ["05:30"])
        self.assertEqual(deps_df["SABADO"], ["06:15"])
        self.assertEqual(deps_df["DOM_FER"], ["07:15"])


if __name__ == "__main__":
    unittest.main()

