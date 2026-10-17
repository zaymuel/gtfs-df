"""
extract.py - Extrator Multithread Resiliente da Rede de Transporte Público do DF (DFTrans / Semob-DF).

Ticket 03:
- Baixa o catálogo mestre de todas as paradas do DF (/parada/geo/paradas -> data/all_stops_df.geojson).
- Processa linhas em paralelo com ThreadPoolExecutor (2 a 4 workers).
- Aplica delay cortês de 1.0s por worker e backoff exponencial com jitter em erros 429/5xx.
- Salva dados brutos de forma atômica (.tmp -> .json) em data/raw/{numero_linha}.json.
- Suporta retomada transparente (ignora linhas já em cache, a menos que --force seja informado).
"""

import bus2_client
from http_client import PoliteClient, HttpRequestError
import config
import argparse
import json
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

# Garante acesso aos módulos (config na raiz, http_client e bus2_client em scripts/)
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def ensure_master_stops(client: PoliteClient, force: bool = False) -> Path:
    """Garante o download do inventário espacial mestre de paradas do DF (atualmente ~5.466 paradas, sujeito a atualização)."""
    stops_path = config.STOPS_MASTER_PATH
    # Verifica se o inventário mestre já foi baixado anteriormente para evitar requisições desnecessárias
    if stops_path.exists() and not force:
        logger.info("Inventário mestre de paradas já existe em %s", stops_path)
        return stops_path

    # Realiza o download do inventário espacial completo via endpoint oficial
    logger.info(
        "Baixando inventário mestre de paradas do DFTrans (/parada/geo/paradas)...")
    url = f"{config.DFTRANS_BASE_URL}/parada/geo/paradas"
    data = client.get_json(url)
    if not data or not isinstance(data, dict) or "features" not in data:
        raise RuntimeError(
            "Falha ao obter inventário mestre de paradas do DFTrans.")

    # Gravação atômica: salva primeiro em arquivo temporário (.tmp) e renomeia
    # Isso evita deixar arquivos JSON corrompidos ou parciais caso o processo seja interrompido
    tmp_path = stops_path.with_suffix(".geojson.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp_path.replace(stops_path)
    logger.info("Inventário mestre de paradas salvo com sucesso em %s (%d feições)",
                stops_path, len(data["features"]))
    return stops_path


def load_catalog(catalog_path: Path) -> List[str]:
    """
    Carrega o catálogo de linhas a partir de data/catalog/lines.json ou fallback em data/lines.json.
    Suporta listas de objetos [{'numero': '...'}, ...] ou listas simples de strings.
    """
    # Verifica existência do catálogo primário com fallback automático para versão legada
    if not catalog_path.exists():
        legacy_path = config.LEGACY_CATALOG_PATH
        if legacy_path.exists():
            logger.warning(
                "Catálogo mestre %s não encontrado. Usando fallback %s", catalog_path, legacy_path)
            catalog_path = legacy_path
        else:
            raise FileNotFoundError(
                f"Nenhum catálogo encontrado em {catalog_path} ou {legacy_path}")

    with open(catalog_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Extrai números de linha com desduplicação e suporte a múltiplos formatos
    # Trata catálogos em formato de lista de dicionários, lista de strings ou mapa chave-valor
    lines: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and "numero" in item:
                num = str(item["numero"]).strip()
                if num and item.get("ativo", True):
                    lines.append(num)
            elif isinstance(item, str) and item.strip():
                lines.append(item.strip())
    elif isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict) and "numero" in v:
                lines.append(str(v["numero"]).strip())
            else:
                lines.append(str(k).strip())

    # Ordena e desduplica para garantir execução determinística e reproduzível
    deduped = sorted(list(set(lines)))
    logger.info("Catálogo carregado de %s: %d linhas válidas para extração",
                catalog_path, len(deduped))
    return deduped


def fetch_line_dftrans(client: PoliteClient, numero: str) -> Optional[Dict[str, Any]]:
    """Busca metadados cadastrais, operadoras e sequenciais da linha no DFTrans."""
    url = f"{config.DFTRANS_BASE_URL}/linha/numero/{numero}"
    try:
        data = client.get_json(url)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data
    except HttpRequestError as e:
        logger.warning("[%s] Erro DFTrans /linha/numero: %s", numero, e)
    return None


def fetch_percursos(client: PoliteClient, numero: str, linha_meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Busca polilinhas em EPSG:3857 para cada sentido da linha."""
    percursos = {}
    url_num = f"{config.DFTRANS_BASE_URL}/percurso/linha/numero/{numero}/"
    try:
        data = client.get_json(url_num)
        if data and isinstance(data, dict) and "features" in data and len(data["features"]) > 0:
            percursos["numero"] = data
            return percursos
    except HttpRequestError:
        pass

    if linha_meta and "sequencial" in linha_meta:
        seq = linha_meta["sequencial"]
        url_seq = f"{config.DFTRANS_BASE_URL}/percurso/linha/{seq}"
        try:
            data = client.get_json(url_seq)
            if data and isinstance(data, dict) and "features" in data:
                percursos[str(seq)] = data
        except HttpRequestError as e:
            logger.debug("[%s] Percurso por seq %s falhou: %s", numero, seq, e)

    return percursos


def fetch_horarios(client: PoliteClient, numero: str, linha_meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Busca partidas oficiais do DFTrans."""
    horarios = {}
    url_num = f"{config.DFTRANS_BASE_URL}/horario/linha/numero/{numero}"
    try:
        data = client.get_json(url_num)
        if data:
            horarios["numero"] = data
            return horarios
    except HttpRequestError:
        pass

    if linha_meta and "sequencial" in linha_meta:
        seq = linha_meta["sequencial"]
        url_seq = f"{config.DFTRANS_BASE_URL}/horario/linha/{seq}"
        try:
            data = client.get_json(url_seq)
            if data:
                horarios[str(seq)] = data
        except HttpRequestError:
            pass

    return horarios


def fetch_bus2_supplement(numero: str, bus2_map: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Busca dados suplementares no Bus2 (timetable e trip-details com travel time offsets)."""
    supp = {}
    if not bus2_map or numero not in bus2_map:
        return supp

    route_info = bus2_map[numero]
    route_id_b36 = route_info.get("routeId")
    if not route_id_b36:
        return supp

    try:
        tt = bus2_client.fetch_timetable(route_id_b36)
        if tt:
            supp["timetable"] = tt
            trips = tt.get("timetable", {}).get("trips", [])
            if trips and isinstance(trips, list) and len(trips) > 0:
                first_trip_hash = trips[0].get("tripId")
                if first_trip_hash:
                    td = bus2_client.fetch_trip_details(first_trip_hash)
                    if td:
                        supp["trip_details"] = td
    except Exception as e:
        logger.debug("[%s] Suplemento Bus2 falhou: %s", numero, e)

    return supp


def process_line_worker(
    numero: str,
    client: PoliteClient,
    force: bool,
    bus2_map: Optional[Dict[str, Any]],
    lock: threading.Lock,
    stats: Dict[str, int]
) -> str:
    """Worker para extração atômica de uma linha individual."""
    out_file = config.RAW_DIR / f"{numero}.json"
    if out_file.exists() and not force:
        with lock:
            stats["skipped"] += 1
        return f"CACHE {numero}"

    linha_meta = fetch_line_dftrans(client, numero)
    percursos = fetch_percursos(client, numero, linha_meta)
    horarios = fetch_horarios(client, numero, linha_meta)
    bus2_data = fetch_bus2_supplement(numero, bus2_map)

    if not linha_meta and not percursos:
        with lock:
            stats["failed"] += 1
        return f"SEM_DADOS {numero}"

    payload = {
        "numero": numero,
        "linha": linha_meta or {},
        "percursos": percursos,
        "horarios": horarios,
        "bus2": bus2_data,
    }

    tmp_file = out_file.with_suffix(".tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_file.replace(out_file)
        with lock:
            stats["saved"] += 1
        return f"OK {numero} (percursos: {len(percursos)}, horarios: {bool(horarios)}, bus2: {bool(bus2_data)})"
    except Exception as e:
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)
        with lock:
            stats["failed"] += 1
        return f"ERRO {numero}: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="Extrator Multithread Resiliente da Rede DFTrans / Semob-DF.")
    parser.add_argument("--lines", type=str, default=None,
                        help="Lista separada por vírgula de linhas específicas para extrair (ex: 0.110,2304)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limitar extração às primeiras N linhas do catálogo")
    parser.add_argument("--catalog", type=str, default=str(config.CATALOG_PATH),
                        help=f"Caminho do catálogo JSON de linhas (padrão: {config.CATALOG_PATH})")
    parser.add_argument("--workers", type=int, default=config.HTTP_WORKERS,
                        help=f"Número de threads simultâneas (padrão: {config.HTTP_WORKERS})")
    parser.add_argument("--delay", type=float, default=config.HTTP_DELAY_SEC,
                        help=f"Delay cortês por worker em segundos (padrão: {config.HTTP_DELAY_SEC}s)")
    parser.add_argument("--retries", type=int, default=config.HTTP_RETRIES,
                        help=f"Número de retentativas em caso de erro (padrão: {config.HTTP_RETRIES})")
    parser.add_argument("--backoff", type=float, default=config.HTTP_BACKOFF_SEC,
                        help=f"Fator de backoff exponencial (padrão: {config.HTTP_BACKOFF_SEC}s)")
    parser.add_argument("--force", action="store_true",
                        help="Forçar re-download de todas as linhas e do inventário mestre")
    args = parser.parse_args()

    # Garante que os diretórios existam
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    config.CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    client = PoliteClient(
        delay=args.delay,
        retries=args.retries,
        backoff=args.backoff,
        timeout=config.HTTP_TIMEOUT_SEC
    )

    # 1. Garante inventário mestre de paradas
    ensure_master_stops(client, force=args.force)

    # 2. Carrega lista de linhas
    if args.lines:
        target_lines = [l.strip() for l in args.lines.split(",") if l.strip()]
    else:
        target_lines = load_catalog(Path(args.catalog))

    if args.limit:
        target_lines = target_lines[:args.limit]

    # 3. Carrega mapa do Bus2 se existente
    bus2_map = None
    if config.BUS2_ROUTE_MAP_PATH.exists():
        try:
            with open(config.BUS2_ROUTE_MAP_PATH, "r", encoding="utf-8") as f:
                bus2_map = json.load(f)
        except Exception as e:
            logger.warning(
                "Não foi possível carregar route_map do Bus2: %s", e)

    total = len(target_lines)
    logger.info("=== Iniciando extração de %d linhas com %d workers (delay: %.1fs) ===",
                total, args.workers, args.delay)

    stats = {"saved": 0, "skipped": 0, "failed": 0}
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_line_worker, num, client, args.force, bus2_map, lock, stats): num
            for num in target_lines
        }
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            if i % 10 == 0 or i == total or "OK" in res or "ERRO" in res:
                print(f"[{i}/{total}] {res}")

    print("\n=== Resumo da Extração ===")
    print(f"Total processado: {total}")
    print(f"Novas extrações salvas: {stats['saved']}")
    print(f"Reaproveitadas do cache: {stats['skipped']}")
    print(f"Falhas/sem metadados: {stats['failed']}")
    print(f"Arquivos disponíveis em: {config.RAW_DIR}")


if __name__ == "__main__":
    main()
