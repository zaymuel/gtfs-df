"""
extract.py - Extrator de Dados do Transporte Público do Distrito Federal (DFTrans / Semob-DF)

Este script automatiza a coleta de dados operacionais, traçados geométricos, paradas
e tabelas horárias a partir da API oficial do DFTrans (https://www.sistemas.dftrans.df.gov.br).

Os dados brutos são salvos em `data/raw/{numero_linha}.json` de forma atômica e com
suporte a retomada (checkpoint/cache local).

Uso:
  python extract.py --limit 5            # Testar com as primeiras 5 linhas
  python extract.py --lines 0.110,2304   # Extrair apenas linhas específicas
  python extract.py                      # Extração completa de todas as linhas (~961)
  python extract.py --force              # Forçar re-download ignorando cache
"""

import os
import sys
import json
import time
import argparse
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional

# Constantes e Endpoints da API DFTrans
BASE_URL = "https://www.sistemas.dftrans.df.gov.br"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json"
}

# Diretórios padrão
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CATALOG_DIR = DATA_DIR / "catalog"
RAW_DIR = DATA_DIR / "raw"


def safe_request(url: str, session: requests.Session, retries: int = 3, backoff: float = 2.0) -> Optional[Any]:
    """
    Executa requisição HTTP GET com mecanismo de retry e exponential backoff.
    """
    for attempt in range(1, retries + 1):
        try:
            resp = session.get(url, headers=DEFAULT_HEADERS, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (404, 204):
                return None
            elif resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff * attempt)
            else:
                resp.raise_for_status()
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            if attempt == retries:
                return None
            time.sleep(backoff * attempt)
    return None


def load_catalog(catalog_path: Path) -> List[str]:
    """
    Carrega o catálogo de linhas a partir do arquivo JSON estruturado.
    Retorna uma lista ordenada de números de linha.
    """
    if not catalog_path.exists():
        # Se não encontrar em data/catalog/lines.json, tenta em data/lines.json
        fallback = DATA_DIR / "lines.json"
        if fallback.exists():
            catalog_path = fallback
        else:
            raise FileNotFoundError(
                f"Catálogo de linhas não encontrado em {catalog_path} ou {fallback}. "
                "Certifique-se de que o catálogo inicial existe."
            )

    with open(catalog_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extrai números de linha com desduplicação
    line_numbers = []
    seen = set()
    for item in data:
        num = item.get("numero") if isinstance(item, dict) else str(item)
        if num and num not in seen:
            seen.add(num)
            line_numbers.append(num)

    return line_numbers


def extract_line(line_number: str, session: requests.Session, delay: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Extrai todos os dados de uma linha específica via API oficial do DFTrans:
    1. Metadados operacionais e sentidos (/linha/numero/{numero})
    2. Geometria de percurso em EPSG:3857 (/percurso/linha/numero/{numero}/)
    3. Paradas por sentido operacional (/parada/linha/{sequencial}/geo)
    4. Tabela de horários de partida (/horario/linha/numero/{numero})
    """
    # 1. Metadados e sentidos
    meta = safe_request(f"{BASE_URL}/linha/numero/{line_number}", session)
    time.sleep(delay)

    if not meta or not isinstance(meta, list):
        return None

    # 2. Geometria de percurso (LineString em EPSG:3857)
    percurso = safe_request(
        f"{BASE_URL}/percurso/linha/numero/{line_number}/", session)
    time.sleep(delay)

    # 3. Paradas por sentido (usando o 'sequencial' interno de cada sentido)
    paradas_por_sentido = {}
    for sentido_info in meta:
        seq = sentido_info.get("sequencial")
        sentido = sentido_info.get("sentido") or "UNICO"
        if seq:
            stops_geojson = safe_request(
                f"{BASE_URL}/parada/linha/{seq}/geo", session)
            if stops_geojson:
                paradas_por_sentido[sentido] = stops_geojson
            time.sleep(delay)

    # 4. Tabela horária
    horarios = safe_request(
        f"{BASE_URL}/horario/linha/numero/{line_number}", session)
    time.sleep(delay)

    return {
        "numero": line_number,
        "metadata": meta,
        "percurso": percurso,
        "paradas": paradas_por_sentido,
        "horarios": horarios
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extrator de dados da API oficial do DFTrans / Semob-DF")
    parser.add_argument("--catalog", type=str, default="data/lines.json",
                        help="Caminho do arquivo de catálogo de linhas")
    parser.add_argument("--lines", type=str, default=None,
                        help="Lista de números de linha separados por vírgula (ex: 0.110,2304)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limite máximo de linhas para extrair (útil para testes)")
    parser.add_argument("--force", action="store_true",
                        help="Força nova extração mesmo se já existir em cache")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Tempo de espera (em segundos) entre requisições")
    args = parser.parse_args()

    # Garante que os diretórios existam
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()

    # Define a lista de linhas
    if args.lines:
        target_lines = [l.strip() for l in args.lines.split(",") if l.strip()]
    else:
        catalog_path = Path(args.catalog)
        target_lines = load_catalog(catalog_path)

    if args.limit:
        target_lines = target_lines[:args.limit]

    total_lines = len(target_lines)
    print(f"=== Iniciando extração de {total_lines} linhas do DFTrans ===")
    print(f"Diretório de destino: {RAW_DIR}")
    print(f"Intervalo entre requisições: {args.delay}s\n")

    saved_count = 0
    skipped_count = 0
    failed_count = 0

    for idx, line_number in enumerate(target_lines, start=1):
        # Sanitiza nome do arquivo (ex: 0.110 -> 0.110.json)
        safe_name = line_number.replace("/", "_")
        cache_file = RAW_DIR / f"{safe_name}.json"

        if cache_file.exists() and not args.force:
            print(f"[{idx}/{total_lines}] Linha {line_number} já em cache (pulando)")
            skipped_count += 1
            continue

        print(f"[{idx}/{total_lines}] Extraindo linha {line_number}...",
              end=" ", flush=True)
        try:
            data = extract_line(line_number, session, delay=args.delay)
            if data and data.get("metadata"):
                # Salva em arquivo temporário e renomeia (gravação atômica)
                tmp_file = RAW_DIR / f"{safe_name}.json.tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tmp_file.replace(cache_file)

                sentidos = [s.get("sentido") for s in data.get("metadata", [])]
                num_stops = sum(len(g.get("features", [])) for g in data.get(
                    "paradas", {}).values() if isinstance(g, dict))
                print(
                    f"OK ({len(sentidos)} sentidos: {', '.join(sentidos)}, {num_stops} paradas)")
                saved_count += 1
            else:
                print("FALHA (metadados nulos ou linha inexistente na API)")
                failed_count += 1
        except Exception as e:
            print(f"ERRO: {e}")
            failed_count += 1

    print("\n=== Resumo da Extração ===")
    print(f"Total processado: {total_lines}")
    print(f"Novas extrações salvas: {saved_count}")
    print(f"Linhas reaproveitadas do cache: {skipped_count}")
    print(f"Linhas sem resposta/com falha: {failed_count}")
    print(f"Arquivos disponíveis em: {RAW_DIR}")


if __name__ == "__main__":
    main()
