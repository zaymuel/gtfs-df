"""
config.py - Configuração centralizada do pipeline DFTrans -> GTFS (r5py).

Localizado em scripts/config.py.
Todos os módulos (discover_catalog.py, extract.py, build_gtfs.py, etc.) leem
parâmetros operacionais, caminhos e constantes de modelagem daqui.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ----------------------------------------------------------------------------
# Caminhos (BASE_DIR aponta para a raiz do projeto)
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# índice mestre de linhas + logs de auditoria
CATALOG_DIR = DATA_DIR / "catalog"

# payloads brutos DFTrans: {numero}.json
RAW_DIR = DATA_DIR / "raw"
BUS2_DIR = DATA_DIR / "bus2 drafts"         # artefatos do Bus2 / DF no Ponto

# cache por linha do Bus2: {numero}.json
BUS2_LINES_DIR = BUS2_DIR / "lines"
GTFS_DIR = DATA_DIR / "gtfs"                # tabelas GTFS e gtfs_df.zip

CATALOG_PATH = CATALOG_DIR / "lines.json"
DISCOVERY_LOG_PATH = CATALOG_DIR / "discovery_log.json"
SKIPPED_LINES_PATH = CATALOG_DIR / "skipped_lines.json"
EXTRACT_FAILURES_PATH = CATALOG_DIR / "extract_failures.json"

# {sequencial_parada: [sequencial_linha, ...]}
STOP_LINES_INDEX_PATH = CATALOG_DIR / "stop_lines.json"

# /parada/geo/paradas (EPSG:3857)
STOPS_MASTER_PATH = DATA_DIR / "all_stops_df.geojson"

# numero DFTrans -> IDs Base36 do Bus2
BUS2_ROUTE_MAP_PATH = CATALOG_DIR / "bus2_route_map.json"

# catálogo completo de rotas da API Bus2
BUS2_ROUTES_PATH = CATALOG_DIR / "bus2_routes.json"

# operadoras/concessionárias cadastradas
BUS2_AGENCIES_PATH = CATALOG_DIR / "bus2_agencies.json"

# catálogo legado (terceiros), só fallback
LEGACY_CATALOG_PATH = DATA_DIR / "lines.json"

# ----------------------------------------------------------------------------
# API oficial DFTrans / Semob-DF
# ----------------------------------------------------------------------------
DFTRANS_BASE_URL = "https://www.sistemas.dftrans.df.gov.br"

# /linha/find/{termo} corta em 30 registros (LIMIT 30 no servidor)
FIND_RESULT_CAP = 30

# alfabeto dos números de linha (dígitos e ponto)
CATALOG_ALPHABET = "0123456789."

# ----------------------------------------------------------------------------
# Bus2 / Mobilibus API (dfnoponto / bus2.info)
# ----------------------------------------------------------------------------

# Hash Base36 do projeto Brasília (ID 5600313)
BUS2_PROJECT_HASH = "3c189"
BUS2_API_BASE = "https://mobilibus.com/api"
BUS2_PAINEL_BASE = "https://painel.mobilibus.com/v2/api/public"

# Passphrase pública extraída dos bundles JS Angular (main.*.js / chunk 244.*.js).
# Permite sobrescrita via variável de ambiente BUS2_ENCRYPTION_KEY se rotacionar.
BUS2_ENCRYPTION_KEY = os.getenv(
    "BUS2_ENCRYPTION_KEY", "GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n")

# ----------------------------------------------------------------------------
# Política de requisições (polidez + resiliência)
# ----------------------------------------------------------------------------
HTTP_WORKERS = 4                # 2-4 workers concorrentes
HTTP_DELAY_SEC = 1.0            # pausa por worker após cada requisição
HTTP_RETRIES = 4                # tentativas por requisição

# backoff exponencial: backoff * 2**(tentativa-1) (+ jitter)
HTTP_BACKOFF_SEC = 2.0
HTTP_TIMEOUT_SEC = 30
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ----------------------------------------------------------------------------
# Modelagem GTFS (ADR 0001 / 0002)
# Permite customização direta no código ou sobrescrita via variáveis de ambiente
# (ex: SPEED_CONVENTIONAL_KMH=25.0 SPEED_BRT_KMH=45.0 DWELL_TIME_SEC=20)
# ----------------------------------------------------------------------------

# velocidade média urbana convencional
SPEED_CONVENTIONAL_KMH = float(os.getenv("SPEED_CONVENTIONAL_KMH", "20.0"))

# BRT em corredor exclusivo (opera até 60 km/h)
SPEED_BRT_KMH = float(os.getenv("SPEED_BRT_KMH", "40.0"))

# tempo de parada em cada ponto intermediário (segundos)
DWELL_TIME_SEC = int(os.getenv("DWELL_TIME_SEC", "30"))

# Web Mercator (EPSG:3857) estica distâncias por 1/cos(lat). Em Brasília (lat ~ -15.8°):
# distância real = distância_3857 * cos(15.8°) ~ 0.9622.
MERCATOR_SCALE_FACTOR = 0.9622

CALENDAR_START = "20260101"
CALENDAR_END = "20261231"
SERVICE_IDS = {"SEG_SEX": "weekday", "SABADO": "saturday", "DOM_FER": "sunday"}

# Caixa envolvente válida do Distrito Federal (WGS84): lat_min, lat_max, lon_min, lon_max.
DF_BBOX = (-16.1, -15.4, -48.3, -47.2)

# Detecção de BRT (Expresso DF Sul / BRT Sul):
# As linhas do sistema BRT não possuem ponto (.) em sua numeração.
# 1. Troncais (21xx, 22xx, 23xx, 24xx): operam em corredor exclusivo a 40 km/h com veículos Padron/Articulado BRT.
# 2. Alimentadoras (32xx Gama, 33xx Santa Maria, ex. 3320): alimentam os terminais de integração em tráfego misto a 20 km/h.
BRT_VEHICLE_KEYWORD = "BRT"
BRT_TRUNK_PREFIXES = ("21", "22", "23", "24")
BRT_FEEDER_PREFIXES = ("32", "33")
BRT_LINE_NUMBERS = {
    "2101", "2201", "2202", "2203", "2205", "2206", "2207", "2208", "2209",
    "2210", "2211", "2212", "2213", "2301", "2302", "2303", "2304", "2306",
    "2307", "2308", "2309", "2310", "2311", "2401"
}


def is_brt_trunk(numero: str, tipos_onibus: Optional[list] = None) -> bool:
    """Verifica se a linha é um serviço troncal do BRT (corredor exclusivo, 40 km/h)."""
    if not numero:
        return False
    num = str(numero).strip()
    if num in BRT_LINE_NUMBERS or any(num.startswith(p) for p in BRT_TRUNK_PREFIXES):
        return True
    if tipos_onibus and isinstance(tipos_onibus, list):
        for t in tipos_onibus:
            desc = t.get("descricao", "").upper()
            if BRT_VEHICLE_KEYWORD in desc:
                return True
    return False


def is_brt_feeder(numero: str) -> bool:
    """Verifica se a linha é alimentadora do BRT (bacias Gama 32xx / Santa Maria 33xx, ex: 3320)."""
    if not numero:
        return False
    num = str(numero).strip()
    return any(num.startswith(p) for p in BRT_FEEDER_PREFIXES) and len(num) == 4


MIN_STOPS_PER_TRIP = 2
AGENCY = {
    "agency_id": "SEMOB-DF",
    "agency_name": "Secretaria de Transporte e Mobilidade do Distrito Federal (SEMOB-DF / DFTrans)",
    "agency_url": "https://www.semob.df.gov.br",
    "agency_timezone": "America/Sao_Paulo",
    "agency_lang": "pt",
}
