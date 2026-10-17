"""
build_gtfs.py - Compilador GTFS Estático para o Distrito Federal (DFTrans / Semob-DF).

Tickets 04, 05, 14, 15:
- Lê dados brutos em data/raw/*.json e paradas mestres em data/all_stops_df.geojson.
- Converte geometrias e coordenadas de EPSG:3857 (Web Mercator) para EPSG:4326 (WGS84).
- Realiza linear referencing com Shapely para ordenar paradas monotonicamente ao longo do percurso.
- Calcula tempos de passagem interpolados diferenciando BRT troncal (40 km/h) e convencional/alimentadoras (20 km/h) + 30s dwell.
- Aplica identidade visual oficial das Bacias (1 a 5) em route_color e route_text_color (Ticket 14).
- Mapeia faixas tarifárias em fare_attributes.txt e fare_rules.txt para custos generalizados de viagem (Ticket 05).
- Suporta todas as 56 linhas sem ponto (.) do sistema BRT Sul (troncais 22xx/23xx/24xx e alimentadoras 32xx/33xx como 3320) (Ticket 15).
- Envia linhas incompletas ou inválidas para data/catalog/skipped_lines.json.
- Gera agency.txt, routes.txt, stops.txt, trips.txt, stop_times.txt, calendar.txt, shapes.txt, fare_attributes.txt, fare_rules.txt e compacta em gtfs_df.zip.
"""

import config
from shapely.strtree import STRtree
from shapely.geometry import LineString, Point
import pyproj
import csv
import json
import logging
import math
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Reprojeção EPSG:3857 -> EPSG:4326 (lon, lat)
TRANSFORMER_3857_TO_4326 = pyproj.Transformer.from_crs(
    "EPSG:3857", "EPSG:4326", always_xy=True)


def to_wgs84(x: float, y: float) -> Tuple[float, float]:
    """Converte coordenadas Web Mercator (x, y em metros) para WGS84 (lon, lat em graus)."""
    lon, lat = TRANSFORMER_3857_TO_4326.transform(x, y)
    return lon, lat


def format_gtfs_time(seconds_from_midnight: int) -> str:
    """Formata segundos a partir da meia-noite no formato HH:MM:SS do GTFS (suporta >= 24h)."""
    h = seconds_from_midnight // 3600
    rem = seconds_from_midnight % 3600
    m = rem // 60
    s = rem % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Converte 'HH:MM' ou 'HH:MM:SS' para segundos desde a meia-noite."""
    if not time_str or not isinstance(time_str, str):
        return None
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 3600 + int(parts[1]) * 60
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return None


def is_in_bbox(lat: float, lon: float) -> bool:
    """Valida se o ponto está contido na bounding box do Distrito Federal."""
    lat_min, lat_max, lon_min, lon_max = config.DF_BBOX
    return (lat_min <= lat <= lat_max) and (lon_min <= lon <= lon_max)


def load_master_stops() -> Dict[str, Dict[str, Any]]:
    """Carrega as paradas mestres de all_stops_df.geojson indexadas por sequencial ou codDftrans."""
    stops = {}
    master_path = config.STOPS_MASTER_PATH
    if not master_path.exists():
        logger.warning(
            "Inventário mestre de paradas não encontrado em %s", master_path)
        return stops

    out_of_bounds_stops: List[Dict[str, Any]] = []

    try:
        with open(master_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            if geom.get("type") != "Point" or not geom.get("coordinates"):
                continue
            x, y = geom["coordinates"][:2]
            lon, lat = to_wgs84(x, y)
            stop_id = str(props.get("sequencial") or props.get(
                "codDftrans") or f"P_{x}_{y}")

            if not is_in_bbox(lat, lon):
                # Trata e audita paradas fora da bounding box do DF (ex: conexões no Entorno ou erros cadastrais)
                out_of_bounds_stops.append({
                    "stop_id": stop_id,
                    "descricao": props.get("descricao") or props.get("logradouro") or f"Parada {stop_id}",
                    "lat": lat,
                    "lon": lon,
                    "x_3857": x,
                    "y_3857": y,
                    "reason": "Coordenadas fora da bounding box regulamentar do DF (config.DF_BBOX)"
                })
                continue

            stops[stop_id] = {
                "stop_id": stop_id,
                "stop_name": props.get("descricao") or props.get("logradouro") or f"Parada {stop_id}",
                "stop_lat": lat,
                "stop_lon": lon,
                # '3857' refere-se ao código EPSG:3857 (WGS 84 / Pseudo-Mercator / Web Mercator).
                # A API do DFTrans serve geometrias nativamente em coordenadas métricas projetadas nessa projeção
                # plana (x ~ -5.330.000m, y ~ -1.780.000m). Mantemos as coordenadas em metros em 'x_3857' e
                # 'y_3857' para permitir cálculos euclidianos e projeção linear com Shapely (LineString.project),
                # enquanto 'stop_lat' e 'stop_lon' (EPSG:4326 em graus WGS84) são exportados para o feed GTFS.
                "x_3857": x,
                "y_3857": y,
                "point_geom": Point(x, y)
            }
        logger.info("Carregadas %d paradas mestres válidas do DF", len(stops))

        if out_of_bounds_stops:
            out_file = config.CATALOG_DIR / "out_of_bounds_stops.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(out_of_bounds_stops, f, indent=2, ensure_ascii=False)
            logger.warning("Registradas %d paradas fora da bounding box do DF em %s",
                           len(out_of_bounds_stops), out_file)
    except Exception as e:
        logger.error("Erro ao ler inventário mestre de paradas: %s", e)
    return stops


class GtfsCompiler:
    def __init__(self):
        config.GTFS_DIR.mkdir(parents=True, exist_ok=True)
        config.CATALOG_DIR.mkdir(parents=True, exist_ok=True)

        self.catalog_map: Dict[str, Dict[str, Any]] = self.load_catalog_map()
        self.master_stops = load_master_stops()
        self.stop_points = [
            s["point_geom"] for s in self.master_stops.values()
        ]
        self.stop_keys = list(self.master_stops.keys())
        self.str_tree = STRtree(self.stop_points) if self.stop_points else None

        # Tabelas GTFS em memória
        self.routes: List[Dict[str, Any]] = []
        self.trips: List[Dict[str, Any]] = []
        self.stops: Dict[str, Dict[str, Any]] = {}
        self.stop_times: List[Dict[str, Any]] = []
        self.shapes: List[Dict[str, Any]] = []
        self.fare_attributes: Dict[str, Dict[str, Any]] = {}
        self.fare_rules: List[Dict[str, Any]] = []
        self.skipped_lines: List[Dict[str, Any]] = []

    def load_catalog_map(self) -> Dict[str, Dict[str, Any]]:
        """Carrega dados cadastrais consolidados (cor, operadora, tarifa) de data/catalog/lines.json."""
        cat_map = {}
        cat_path = config.CATALOG_PATH
        if cat_path.exists():
            try:
                with open(cat_path, "r", encoding="utf-8") as f:
                    items = json.load(f)
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "numero" in item:
                            cat_map[str(item["numero"]).strip()] = item
            except Exception as e:
                logger.warning(
                    "Falha ao carregar catálogo mestre %s: %s", cat_path, e)
        return cat_map

    def get_line_speed(self, numero: str, tipos_onibus: Optional[List[Dict[str, Any]]]) -> Tuple[float, bool]:
        """Determina velocidade de operação e flag de BRT troncal (Ticket 15)."""
        if config.is_brt_trunk(numero, tipos_onibus):
            return config.SPEED_BRT_KMH, True
        return config.SPEED_CONVENTIONAL_KMH, False

    def get_route_colors(self, numero: str, is_brt: bool) -> Tuple[str, str]:
        """Obtém route_color e route_text_color de alto contraste baseados na Bacia/Operadora (Ticket 14)."""
        cat_info = self.catalog_map.get(numero, {})
        cor_hex = cat_info.get("cor")
        if cor_hex and isinstance(cor_hex, str):
            clean_hex = cor_hex.strip().lstrip("#").upper()
            if len(clean_hex) == 6:
                try:
                    r = int(clean_hex[0:2], 16)
                    g = int(clean_hex[2:4], 16)
                    b = int(clean_hex[4:6], 16)
                    luminance = 0.299 * r + 0.587 * g + 0.114 * b
                    text_color = "000000" if luminance > 140 else "FFFFFF"
                    return clean_hex, text_color
                except ValueError:
                    pass

        # Fallback padronizado
        if is_brt:
            return "E60000", "FFFFFF"
        return "175898", "FFFFFF"

    def compile_all(self):
        logger.info("Iniciando compilação GTFS a partir de %s...",
                    config.RAW_DIR)
        raw_files = list(config.RAW_DIR.glob("*.json"))
        if not raw_files:
            logger.warning(
                "Nenhum arquivo bruto encontrado em %s para compilação.", config.RAW_DIR)
            return

        for raw_file in raw_files:
            self.process_raw_line(raw_file)

        self.write_gtfs_tables()
        self.save_skipped_lines()
        self.create_zip()

    def process_raw_line(self, raw_path: Path):
        numero = raw_path.stem
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.skipped_lines.append(
                {"numero": numero, "reason": f"Erro de leitura JSON: {e}"})
            return

        # Suporte a formatos novos (extract.py) e amostras legadas (harvest_dftrans.py)
        linha_meta = data.get("linha") or (
            data.get("metadata")[0]
            if
            isinstance(data.get("metadata"), list)
            and len(data.get("metadata")) > 0
            else {}
        ) or {}
        percursos = data.get("percursos") or {}
        if not percursos and "percurso" in data:
            percursos = {"default": data["percurso"]}
        horarios = data.get("horarios") or data.get("horario") or {}
        bus2_data = data.get("bus2") or {}

        if not percursos:
            self.skipped_lines.append(
                {"numero": numero, "reason": "Sem dados de percurso geométrico"})
            return

        cat_info = self.catalog_map.get(numero, {})
        speed_kmh, is_brt_line = self.get_line_speed(
            numero, linha_meta.get("tiposOnibus"))
        speed_mps = (speed_kmh * 1000.0) / 3600.0
        route_color, route_text_color = self.get_route_colors(
            numero, is_brt_line)

        # Cadastra rota em routes.txt
        route_id = f"R_{numero}"
        desc = linha_meta.get("descricao") or cat_info.get(
            "descricao") or f"Linha {numero}"
        self.routes.append({
            "route_id": route_id,
            "agency_id": config.AGENCY["agency_id"],
            "route_short_name": numero,
            "route_long_name": desc,
            "route_type": "3",  # Bus
            "route_color": route_color,
            "route_text_color": route_text_color
        })

        # Modelagem Tarifária (Ticket 05)
        tarifa: Optional[float] = None
        faixa = linha_meta.get("faixaTarifaria")
        if isinstance(faixa, dict) and "tarifa" in faixa and faixa["tarifa"] is not None:
            try:
                tarifa = float(faixa["tarifa"])
            except ValueError:
                pass
        elif cat_info.get("tarifa") is not None:
            try:
                tarifa = float(cat_info["tarifa"])
            except ValueError:
                pass

        if tarifa is not None and tarifa > 0:
            fare_id = f"F_{int(round(tarifa * 100)):03d}"
            if fare_id not in self.fare_attributes:
                self.fare_attributes[fare_id] = {
                    "fare_id": fare_id,
                    "price": f"{tarifa:.2f}",
                    "currency_type": "BRL",
                    "payment_method": "0",  # Pago a bordo
                    "transfers": "",        # Permite modelagem flexível de integração
                    "agency_id": config.AGENCY["agency_id"]
                }
            self.fare_rules.append({
                "fare_id": fare_id,
                "route_id": route_id
            })

        # Processa cada direção/percurso
        for sentido_key, percurso_data in percursos.items():
            sentido_upper = sentido_key.upper()
            dir_id = "0" if "IDA" in sentido_upper or "CIRC" in sentido_upper else "1"
            features = percurso_data.get("features", [])
            if not features:
                continue

            # Extrai LineString em EPSG:3857
            coords_3857 = []
            for feat in features:
                g = feat.get("geometry", {})
                if g.get("type") == "LineString":
                    coords_3857.extend(g.get("coordinates", []))
                elif g.get("type") == "MultiLineString":
                    for part in g.get("coordinates", []):
                        coords_3857.extend(part)

            if len(coords_3857) < 2:
                continue

            shape_id = f"shp_{numero}_{dir_id}"
            line_3857 = LineString(coords_3857)

            # Grava shapes.txt
            cum_dist = 0.0
            prev_pt = coords_3857[0]
            for seq, pt in enumerate(coords_3857, 1):
                dx = pt[0] - prev_pt[0]
                dy = pt[1] - prev_pt[1]
                cum_dist += math.sqrt(dx * dx + dy * dy) * \
                    config.MERCATOR_SCALE_FACTOR
                prev_pt = pt

                lon, lat = to_wgs84(pt[0], pt[1])
                if is_in_bbox(lat, lon):
                    self.shapes.append({
                        "shape_id": shape_id,
                        "shape_pt_lat": f"{lat:.6f}",
                        "shape_pt_lon": f"{lon:.6f}",
                        "shape_pt_sequence": seq,
                        "shape_dist_traveled": f"{cum_dist:.2f}"
                    })

            # Identifica e projeta paradas ao longo da linha
            stops_for_line = self.snap_stops_along_line(
                line_3857, bus2_data, sentido_upper)
            if len(stops_for_line) < config.MIN_STOPS_PER_TRIP:
                self.skipped_lines.append({
                    "numero": numero,
                    "sentido": sentido_key,
                    "reason": f"Menos de {config.MIN_STOPS_PER_TRIP} paradas identificadas ao longo do traçado"
                })
                continue

            # Obtém partidas
            departures = self.extract_departures(
                horarios, bus2_data, sentido_upper)
            if not departures:
                self.skipped_lines.append({
                    "numero": numero,
                    "sentido": sentido_key,
                    "reason": "Sem partidas/tabelas horárias cadastradas"
                })
                continue

            # Cria trips e stop_times
            for service_id, dep_list in departures.items():
                for trip_idx, dep_time in enumerate(dep_list, 1):
                    trip_id = f"T_{numero}_{dir_id}_{service_id}_{trip_idx}"
                    self.trips.append({
                        "route_id": route_id,
                        "service_id": service_id,
                        "trip_id": trip_id,
                        "trip_headsign": desc,
                        "direction_id": dir_id,
                        "shape_id": shape_id
                    })

                    dep_sec = parse_time_to_seconds(dep_time)
                    if dep_sec is None:
                        continue

                    curr_sec = dep_sec
                    prev_dist = 0.0

                    for stop_seq, (stop_info, dist_m) in enumerate(stops_for_line, 1):
                        self.stops[stop_info["stop_id"]] = stop_info
                        delta_dist = max(0.0, dist_m - prev_dist)
                        transit_time = delta_dist / speed_mps
                        curr_sec += int(transit_time)

                        arr_str = format_gtfs_time(curr_sec)
                        curr_sec += config.DWELL_TIME_SEC \
                            if stop_seq < len(stops_for_line) else 0
                        dep_str = format_gtfs_time(curr_sec)
                        prev_dist = dist_m

                        self.stop_times.append({
                            "trip_id": trip_id,
                            "arrival_time": arr_str,
                            "departure_time": dep_str,
                            "stop_id": stop_info["stop_id"],
                            "stop_sequence": stop_seq,
                            "shape_dist_traveled": f"{dist_m:.2f}"
                        })

    def snap_stops_along_line(self, line_3857: LineString, bus2_data: Dict[str, Any], sentido: str) -> List[Tuple[Dict[str, Any], float]]:
        """Seleciona e ordena monotonicamente as paradas ao longo da linha em EPSG:3857."""
        projected_stops = []

        # 1. Tenta usar lista ordenada do Bus2 se disponível
        bus2_stops = self.extract_bus2_stops(bus2_data, sentido)
        if len(bus2_stops) >= config.MIN_STOPS_PER_TRIP:
            curr_dist = 0.0
            for s in bus2_stops:
                pt = Point(s["x_3857"], s["y_3857"])
                proj_dist = line_3857.project(pt) \
                    * config.MERCATOR_SCALE_FACTOR
                # Garante estrita monotonicidade
                curr_dist = max(curr_dist + 5.0, proj_dist)
                projected_stops.append((s, curr_dist))
            return projected_stops

        # 2. Fallback espacial: Buffer de 35 metros sobre as paradas mestres
        if not self.str_tree:
            return []

        buffer_geom = line_3857.buffer(35.0)
        candidate_idxs = self.str_tree.query(buffer_geom)

        for idx in candidate_idxs:
            pt = self.stop_points[idx]
            if buffer_geom.contains(pt):
                stop_key = self.stop_keys[idx]
                stop_info = self.master_stops[stop_key]
                proj_dist = line_3857.project(pt) \
                    * config.MERCATOR_SCALE_FACTOR
                projected_stops.append((stop_info, proj_dist))

        # Ordena monotonicamente pela distância linear ao longo do traçado
        projected_stops.sort(key=lambda item: item[1])

        # Remove duplicatas muito próximas (< 15 metros)
        deduped = []
        last_d = -999.0
        for s, d in projected_stops:
            if (d - last_d) >= 15.0:
                deduped.append((s, d))
                last_d = d

        return deduped

    def extract_bus2_stops(self, bus2_data: Dict[str, Any], sentido: str) -> List[Dict[str, Any]]:
        """Extrai paradas e coordenadas do cache do Bus2 se disponíveis."""
        stops = []
        trip_details = bus2_data.get("trip_details", {})
        for s in trip_details.get("stops", []):
            lat = s.get("lat")
            lng = s.get("lng")
            if lat and lng and is_in_bbox(lat, lng):
                # Reprojeta WGS84 -> 3857 para projeção linear
                x, y = pyproj.Transformer.from_crs(
                    "EPSG:4326", "EPSG:3857", always_xy=True
                ).transform(lng, lat)
                stop_id = str(s.get("stopId") or f"B2_{lat}_{lng}")
                stops.append({
                    "stop_id": stop_id,
                    "stop_name": s.get("name") or f"Parada {stop_id}",
                    "stop_lat": lat,
                    "stop_lon": lng,
                    "x_3857": x,
                    "y_3857": y
                })
        return stops

    def extract_departures(self, horarios: Dict[str, Any], bus2_data: Dict[str, Any], sentido: str) -> Dict[str, List[str]]:
        """Extrai tabelas de partidas agrupadas por calendário (SEG_SEX, SABADO, DOM_FER)."""
        departures = {}

        # 1. Tenta extrair do Bus2 timetable
        b2_tt = bus2_data.get("timetable", {})
        for direction in b2_tt.get("directions", []):
            for service in direction.get("services", []):
                desc = service.get("desc", "").upper()
                svc_id = "SEG_SEX"
                if "SÁB" in desc or "SAB" in desc:
                    svc_id = "SABADO"
                elif "DOM" in desc or "FERIADO" in desc:
                    svc_id = "DOM_FER"

                deps = [d.get("dep") for d in service.get(
                    "departures", []
                ) if d.get("dep")]
                if deps:
                    departures.setdefault(svc_id, []).extend(deps)

        if departures:
            return departures

        # 2. Fallback para horários DFTrans
        for key, schedule in horarios.items():
            if isinstance(schedule, list):
                for item in schedule:
                    dias = str(
                        item.get("dias") or item.get("tipoDia") or ""
                    ).upper()
                    hora = item.get("horario") or item.get("hora")
                    if not hora:
                        continue
                    svc_id = "SEG_SEX"
                    if "SAB" in dias:
                        svc_id = "SABADO"
                    elif "DOM" in dias:
                        svc_id = "DOM_FER"
                    departures.setdefault(svc_id, []).append(hora)

        return departures

    def write_gtfs_tables(self):
        gtfs_dir = config.GTFS_DIR
        logger.info("Escrevendo tabelas GTFS em %s...", gtfs_dir)

        # 1. agency.txt
        with open(gtfs_dir / "agency.txt", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                               "agency_id", "agency_name", "agency_url",
                               "agency_timezone", "agency_lang"
                               ])
            w.writeheader()
            w.writerow(config.AGENCY)

        # 2. calendar.txt
        with open(gtfs_dir / "calendar.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["service_id", "monday", "tuesday", "wednesday", "thursday",
                      "friday", "saturday", "sunday", "start_date", "end_date"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerow({"service_id": "SEG_SEX", "monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1,
                       "saturday": 0, "sunday": 0, "start_date": config.CALENDAR_START, "end_date": config.CALENDAR_END})
            w.writerow({"service_id": "SABADO", "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0,
                       "saturday": 1, "sunday": 0, "start_date": config.CALENDAR_START, "end_date": config.CALENDAR_END})
            w.writerow({"service_id": "DOM_FER", "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0,
                       "saturday": 0, "sunday": 1, "start_date": config.CALENDAR_START, "end_date": config.CALENDAR_END})

        # 3. routes.txt
        with open(gtfs_dir / "routes.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["route_id", "agency_id", "route_short_name",
                      "route_long_name", "route_type", "route_color", "route_text_color"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.routes)

        # 4. stops.txt
        with open(gtfs_dir / "stops.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["stop_id", "stop_name", "stop_lat", "stop_lon"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for s in self.stops.values():
                w.writerow({
                    "stop_id": s["stop_id"],
                    "stop_name": s["stop_name"],
                    "stop_lat": f"{s['stop_lat']:.6f}",
                    "stop_lon": f"{s['stop_lon']:.6f}"
                })

        # 5. shapes.txt
        with open(gtfs_dir / "shapes.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["shape_id", "shape_pt_lat", "shape_pt_lon",
                      "shape_pt_sequence", "shape_dist_traveled"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.shapes)

        # 6. trips.txt
        with open(gtfs_dir / "trips.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["route_id", "service_id", "trip_id",
                      "trip_headsign", "direction_id", "shape_id"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.trips)

        # 7. stop_times.txt
        with open(gtfs_dir / "stop_times.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["trip_id", "arrival_time", "departure_time",
                      "stop_id", "stop_sequence", "shape_dist_traveled"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.stop_times)

        # 8. fare_attributes.txt (Ticket 05)
        with open(gtfs_dir / "fare_attributes.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["fare_id", "price", "currency_type",
                      "payment_method", "transfers", "agency_id"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.fare_attributes.values())

        # 9. fare_rules.txt (Ticket 05)
        with open(gtfs_dir / "fare_rules.txt", "w", encoding="utf-8", newline="") as f:
            fields = ["fare_id", "route_id"]
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(self.fare_rules)

        logger.info("Tabelas GTFS gravadas com sucesso: %d rotas, %d viagens, %d paradas, %d stop_times, %d tarifas.",
                    len(self.routes), len(self.trips), len(self.stops), len(self.stop_times), len(self.fare_attributes))

    def save_skipped_lines(self):
        out_path = config.SKIPPED_LINES_PATH
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.skipped_lines, f, indent=2, ensure_ascii=False)
        logger.info("Log de linhas ignoradas salvo em %s (%d registros)",
                    out_path, len(self.skipped_lines))

    def create_zip(self):
        zip_path = config.GTFS_DIR / "gtfs_df.zip"
        files_to_zip = [
            "agency.txt", "calendar.txt", "routes.txt", "stops.txt",
            "trips.txt", "stop_times.txt", "shapes.txt",
            "fare_attributes.txt", "fare_rules.txt"
        ]
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in files_to_zip:
                fpath = config.GTFS_DIR / fname
                if fpath.exists():
                    zf.write(fpath, arcname=fname)
        logger.info("Dataset GTFS empacotado com sucesso em: %s (%.2f KB)",
                    zip_path, zip_path.stat().st_size / 1024.0)


def main():
    compiler = GtfsCompiler()
    compiler.compile_all()


if __name__ == "__main__":
    main()
