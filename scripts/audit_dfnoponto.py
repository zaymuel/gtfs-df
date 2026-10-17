"""
audit_dfnoponto.py - Auditoria do portal dfnoponto.com.br, dfnoponto.semob.df.gov.br e Brasília Mobilidade.

Ticket 06 / Ticket 12 / Ticket 13:
- Inspeciona páginas principais e arquivos offline em data/htmls/.
- Compara a cobertura das 961 linhas do portal Brasília Mobilidade contra as 933 linhas de data/catalog/lines.json.
- Analisa a viabilidade e os mecanismos de raspagem de atualizações oficiais de linhas da Semob-DF.
"""

import config
from http_client import PoliteClient, HttpRequestError
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HTMLS_DIR = ROOT / "data" / "htmls"
CATALOG_PATH = config.CATALOG_PATH
BUS2_ROUTES_PATH = config.BUS2_ROUTES_PATH


def audit_offline_htmls(catalog_lines: Set[str]) -> Dict[str, Any]:
    """Inspeciona arquivos HTML offline em busca de catálogos de linhas."""
    offline_files = list(HTMLS_DIR.glob("*.html"))
    logger.info("Encontrados %d arquivos HTML offline em %s",
                len(offline_files), HTMLS_DIR)

    html_lines = {}
    for f in offline_files:
        content = f.read_text(encoding="utf-8", errors="ignore")
        iframes = re.findall(
            r'<iframe[^>]+src=["\']([^"\']+)["\']', content, re.I)

        lines_found = set(re.findall(
            r'class="linha-numero">\s*([0-9A-Za-z.]+)\s*<', content))
        if not lines_found:
            lines_found = set(re.findall(
                r'data-fav-numero=["\']([0-9A-Za-z.]+)["\']', content))

        if lines_found:
            html_lines[f.name] = lines_found
            logger.info("  %s: %d linhas extraídas do DOM (iframes: %d)",
                        f.name, len(lines_found), len(iframes))

    return html_lines


def audit_live_endpoints(catalog_lines: Set[str], client: Optional[PoliteClient] = None) -> Dict[str, Any]:
    """
    Audita a home e endpoints públicos de dfnoponto.com.br e dfnoponto.semob.df.gov.br.
    Utiliza PoliteClient com retries automáticos, backoff exponencial e detecção de redirecionamentos.
    """
    if client is None:
        client = PoliteClient(delay=config.HTTP_DELAY_SEC, retries=config.HTTP_RETRIES)

    targets = [
        ("dfnoponto_com_br", "https://dfnoponto.com.br/"),
        ("dfnoponto_semob", "https://dfnoponto.semob.df.gov.br/"),
    ]

    results = {}
    for label, url in targets:
        logger.info("Consultando portal online com retry e backoff: %s...", url)
        try:
            r = client.get_response(url)
            text = r.text
            iframes = re.findall(
                r'<iframe[^>]+src=["\']([^"\']+)["\']', text, re.I)
            candidates = set(re.findall(
                r'\b\d{1,3}\.\d{1,3}\b|\b\d{4}\b', text))
            valid = {c for c in candidates if c in catalog_lines}

            results[label] = {
                "status": r.status_code,
                "final_url": str(r.url),
                "length": len(text),
                "iframes": iframes,
                "recognized_lines": len(valid),
            }
            logger.info("  [%s] Status: %d, Tamanho: %d bytes, Iframes: %s, Linhas reconhecidas: %d",
                        label, r.status_code, len(text), iframes, len(valid))
        except HttpRequestError as e:
            logger.warning(
                "  [%s] Falha na consulta online com retries esgotados (%s): %s", label, url, e)
            results[label] = {"error": str(e)}
        except Exception as e:
            logger.warning(
                "  [%s] Erro inesperado na consulta online (%s): %s", label, url, e)
            results[label] = {"error": str(e)}

    return results


def main():
    logger.info(
        "=== AUDITORIA DO PORTAL DF NO PONTO & CATÁLOGO BRASÍLIA MOBILIDADE ===")

    # 1. Carrega catálogo mestre
    catalog_lines = set()
    if CATALOG_PATH.exists():
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            cat_data = json.load(f)
            catalog_lines = {x["numero"] for x in cat_data if x.get("numero")}
    logger.info("Catálogo mestre lines.json: %d linhas", len(catalog_lines))

    # 2. Audita arquivos offline
    html_lines = audit_offline_htmls(catalog_lines)

    # 3. Compara com Brasília Mobilidade
    bm_lines = set()
    for fname, lines in html_lines.items():
        if "Todas as linhas" in fname:
            bm_lines = lines
            break

    if bm_lines:
        antt_lines = {l for l in bm_lines if len(l) == 8 and l.isdigit()}
        df_lines = bm_lines - antt_lines
        in_catalog_not_bm = catalog_lines - bm_lines
        in_bm_not_catalog = df_lines - catalog_lines

        logger.info("Reconciliação Brasília Mobilidade:")
        logger.info("  Total de cards: %d", len(bm_lines))
        logger.info("  Linhas interestaduais ANTT (8 dígitos): %d",
                    len(antt_lines))
        logger.info("  Linhas urbanas DF no portal: %d", len(df_lines))
        logger.info("  Linhas presentes no cadastro mestre mas ausentes no portal (%d): %s",
                    len(in_catalog_not_bm), sorted(list(in_catalog_not_bm)))
        logger.info("  Linhas urbanas do portal ausentes no cadastro mestre: %d", len(
            in_bm_not_catalog))

    # 4. Inspeciona endpoints live com cliente HTTP polido e resiliente
    client = PoliteClient()
    live_results = audit_live_endpoints(catalog_lines, client=client)

    logger.info("Auditoria finalizada com sucesso.")


if __name__ == "__main__":
    main()
