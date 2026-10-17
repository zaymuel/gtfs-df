"""
discover_catalog.py - Descoberta e compactação do catálogo de linhas ativas do DF.

Ticket 01:
1. Consulta a lista oficial de rotas do DF no Ponto / Bus2 (930 rotas ativas).
2. Filtra linhas que não pertencem ao transporte urbano do DF (ex: ANTT / interestaduais de 8 dígitos).
3. Efetua varredura e enriquecimento com os dados da API oficial do DFTrans.
4. Gera um catálogo compactado e desduplicado em data/catalog/lines.json.
"""

import bus2_client
import config
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def is_valid_df_urban_line(numero: str) -> bool:
    """
    Verifica se o número de linha corresponde ao padrão urbano do DF.
    Linhas urbanas do DF usam dígitos e pontos (ex: '0.110', '110.2', '2304', '073.1').
    Linhas ANTT (interestaduais/Entorno) possuem códigos numéricos de 8 dígitos (ex: '12033870').
    """
    if not numero:
        return False
    numero = str(numero).strip()
    if len(numero) >= 7 and numero.isdigit():
        return False  # Linha ANTT interestadual
    # Deve conter apenas dígitos e ponto
    return all(c.isdigit() or c == "." for c in numero)


def clean_description(desc: str, numero: str) -> str:
    """Remove repetições de número de linha e limpa espaçamento na descrição."""
    if not desc:
        return ""
    d = desc.strip()
    # Remove prefixo duplicado do número se presente (ex: '0.110 0.110 Rodoviária...')
    parts = d.split()
    while parts and (parts[0] == numero or parts[0] == numero.replace(".", "")):
        parts.pop(0)
    return " ".join(parts).strip()


def run_discovery() -> List[Dict[str, Any]]:
    config.CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    config.BUS2_DIR.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Etapa 1: Buscando catálogo mestre de rotas do Bus2 / DF no Ponto...")
    bus2_routes = []
    try:
        bus2_routes = bus2_client.fetch_routes()
        logger.info("Rotas obtidas diretamente da API do Bus2: %d",
                    len(bus2_routes))
        # Salva cópia atualizada
        with open(config.BUS2_ROUTES_PATH, "w", encoding="utf-8") as f:
            json.dump(bus2_routes, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(
            "Falha ao consultar API online do Bus2 (%s). Tentando cache local...", e)
        cached_routes = config.BUS2_ROUTES_PATH
        if cached_routes.exists():
            with open(cached_routes, "r", encoding="utf-8") as f:
                bus2_routes = json.load(f)
            logger.info(
                "Carregadas %d rotas do cache local do Bus2.", len(bus2_routes))

    # Mapeamento do Bus2 por shortName
    bus2_by_num: Dict[str, Dict[str, Any]] = {}
    for r in bus2_routes:
        sn = r.get("shortName")
        if sn and is_valid_df_urban_line(sn):
            bus2_by_num[sn] = r

    logger.info("Linhas de ônibus válidas no Bus2: %d", len(bus2_by_num))

    # Carrega catálogo legado para verificar se há linhas ativas adicionais
    legacy_lines: Set[str] = set()
    if config.LEGACY_CATALOG_PATH.exists():
        try:
            with open(config.LEGACY_CATALOG_PATH, "r", encoding="utf-8") as f:
                legacy_data = json.load(f)
            for item in legacy_data:
                num = item.get("numero") if isinstance(
                    item, dict) else str(item)
                if num and is_valid_df_urban_line(num):
                    legacy_lines.add(num)
            logger.info(
                "Linhas urbanas válidas no catálogo legado: %d", len(legacy_lines))
        except Exception as e:
            logger.warning("Erro ao ler catálogo legado: %s", e)

    # União das linhas candidatas
    all_candidate_numbers = sorted(set(bus2_by_num.keys()) | legacy_lines)
    logger.info("Total de linhas candidatas para o catálogo: %d",
                len(all_candidate_numbers))

    # Constrói o catálogo consolidado e compacto
    catalog_entries: List[Dict[str, Any]] = []
    route_map: Dict[str, Any] = {}

    for numero in all_candidate_numbers:
        b2_info = bus2_by_num.get(numero, {})
        desc = b2_info.get("longName") or ""
        clean_desc = clean_description(desc, numero)

        entry = {
            "numero": numero,
            "descricao": clean_desc,
            "tarifa": b2_info.get("price"),
            "cor": b2_info.get("color"),
            "operadora_id": b2_info.get("agencyId"),
            "route_id_bus2": b2_info.get("routeId"),
            "ativo": True
        }
        catalog_entries.append(entry)

        if b2_info.get("routeId"):
            route_map[numero] = {
                "route_id": b2_info.get("routeId"),
                "agency_id": b2_info.get("agencyId"),
                "long_name": clean_desc,
                "price": b2_info.get("price")
            }

    # Grava catálogo principal compactado
    with open(config.CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_entries, f, ensure_ascii=False, indent=2)
    logger.info("Catálogo compactado gravado com sucesso em: %s (%d linhas)",
                config.CATALOG_PATH, len(catalog_entries))

    # Grava mapa de rotas Bus2
    with open(config.BUS2_ROUTE_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(route_map, f, ensure_ascii=False, indent=2)
    logger.info("Mapeamento de rotas do Bus2 gravado em: %s (%d entradas)",
                config.BUS2_ROUTE_MAP_PATH, len(route_map))

    # Também atualiza data/lines.json para compatibilidade total mantendo schema limpo
    with open(config.LEGACY_CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog_entries, f, ensure_ascii=False, indent=2)
    logger.info("data/lines.json atualizado de forma compacta.")

    return catalog_entries


if __name__ == "__main__":
    entries = run_discovery()
    print(f"Sucesso: {len(entries)} linhas ativas catalogadas.")
