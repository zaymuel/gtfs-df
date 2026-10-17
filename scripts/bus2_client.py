"""
bus2_client.py - Cliente para a API pública do Bus2 / Mobilibus usada pelo portal oficial
DF no Ponto (https://dfnoponto.semob.df.gov.br/pesquisa-por-linhas/ -> bus2.info/reports/2you/3c189).

Descobertas (engenharia reversa do bundle Angular `main.*.js`, ver docs/03-bus2-reverse-engineering.md):

  * Projeto Bus2 do DF: ``project_hash = "3c189"`` (Base36 de 5600313).
  * Endpoints de relatório (JSON em texto claro):
        GET https://mobilibus.com/api/routes?project_hash=3c189     -> catálogo mestre (routeId Base36 + shortName)
        GET https://mobilibus.com/api/agencies?project_hash=3c189   -> operadoras
  * Endpoints públicos "painel" (resposta ``{"data": "<AES/OpenSSL base64>"}``):
        GET https://painel.mobilibus.com/v2/api/public/get-trips/?ph=3c189&rsn={shortName}
        GET https://painel.mobilibus.com/v2/api/public/get-trip-template/{tripId}
    A cifra é CryptoJS ``AES.decrypt(data, passphrase)`` (formato OpenSSL ``Salted__`` + EVP_BytesToKey/MD5).
    A passphrase é a constante pública embutida no próprio bundle servido anonimamente pelo portal
    (mesma operação que o navegador faz ao abrir a página); não há autenticação envolvida.
"""

import base64
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from config import (
        BUS2_PROJECT_HASH as PROJECT_HASH,
        BUS2_API_BASE as REPORT_API,
        BUS2_PAINEL_BASE as PAINEL_PUBLIC_API,
        BUS2_ENCRYPTION_KEY as PASSPHRASE,
    )
except ImportError:
    import os
    PROJECT_HASH = "3c189"
    REPORT_API = "https://mobilibus.com/api"
    PAINEL_PUBLIC_API = "https://painel.mobilibus.com/v2/api/public"
    PASSPHRASE = os.getenv("BUS2_ENCRYPTION_KEY",
                           "GC]hBB[j_QQ&fZ9=GEJ2>e9!Tv2n")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

_B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def base36_decode(token: str) -> int:
    """'kt6a' -> 970930."""
    return int(token, 36)


def base36_encode(num: int) -> str:
    """970930 -> 'kt6a'."""
    if num == 0:
        return "0"
    chars = []
    while num > 0:
        num, rem = divmod(num, 36)
        chars.append(_B36[rem])
    return "".join(reversed(chars))


def _evp_bytes_to_key(passphrase: bytes, salt: bytes, key_len: int = 32, iv_len: int = 16):
    """OpenSSL EVP_BytesToKey com MD5 (derivação usada pelo CryptoJS com passphrase)."""
    d = d_i = b""
    while len(d) < key_len + iv_len:
        d_i = hashlib.md5(d_i + passphrase + salt).digest()
        d += d_i
    return d[:key_len], d[key_len:key_len + iv_len]


def decrypt_payload(token: str, passphrase: str = PASSPHRASE) -> Any:
    """Decifra o campo ``data`` (CryptoJS AES/OpenSSL base64) e devolve o JSON."""
    raw = base64.b64decode(token)
    if raw[:8] != b"Salted__":
        raise ValueError("Payload não está no formato OpenSSL 'Salted__'")
    salt, ciphertext = raw[8:16], raw[16:]
    key, iv = _evp_bytes_to_key(passphrase.encode("utf-8"), salt)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return json.loads(plain.decode("utf-8"))


def _get_json(url: str, params: Optional[Dict[str, Any]] = None, session: Optional[requests.Session] = None,
              retries: int = 3, backoff: float = 2.0) -> Optional[Any]:
    """GET com retry/backoff exponencial. Devolve JSON (decifrando ``{"data": ...}`` se necessário)."""
    s = session or requests
    for attempt in range(1, retries + 1):
        try:
            resp = s.get(url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                body = resp.json()
                if isinstance(body, dict) and set(body.keys()) == {"data"} and isinstance(body["data"], str):
                    return decrypt_payload(body["data"])
                return body
            if resp.status_code in (404, 204):
                return None
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(backoff * 2 ** (attempt - 1))
                continue
            resp.raise_for_status()
        except (requests.exceptions.RequestException, ValueError):
            if attempt == retries:
                return None
            time.sleep(backoff * 2 ** (attempt - 1))
    return None


def fetch_routes(session: Optional[requests.Session] = None, project_hash: str = PROJECT_HASH) -> List[Dict[str, Any]]:
    """Catálogo mestre: [{routeId, agencyId, shortName, longName, price, ...}]."""
    return _get_json(f"{REPORT_API}/routes", {"project_hash": project_hash}, session) or []


def fetch_agencies(session: Optional[requests.Session] = None, project_hash: str = PROJECT_HASH) -> List[Dict[str, Any]]:
    return _get_json(f"{REPORT_API}/agencies", {"project_hash": project_hash}, session) or []


def fetch_trips(short_name: str, session: Optional[requests.Session] = None,
                project_hash: str = PROJECT_HASH) -> Optional[Any]:
    """Trips (sentidos) da rota identificada pelo shortName (= número da linha DFTrans)."""
    return _get_json(f"{PAINEL_PUBLIC_API}/get-trips/", {"ph": project_hash, "rsn": short_name}, session)


def fetch_trip_template(trip_id: Any, session: Optional[requests.Session] = None) -> Optional[Any]:
    """Template do trip: paradas, shape e (quando disponível) horários."""
    return _get_json(f"{PAINEL_PUBLIC_API}/get-trip-template/{trip_id}", None, session)


def fetch_timetable(route_id_b36: str, session: Optional[requests.Session] = None) -> Optional[Dict[str, Any]]:
    """Tabela de horários e partidas por serviço (dias úteis, sábado, domingo): GET /api/timetable?v=2&route_hash={routeId}."""
    return _get_json(f"{REPORT_API}/timetable", {"v": "2", "route_hash": route_id_b36}, session)


def fetch_trip_details(trip_id_b36: str, session: Optional[requests.Session] = None) -> Optional[Dict[str, Any]]:
    """Detalhes espaciais e temporais do percurso (paradas com offset em segundos 'int'): GET /api/trip-details?v=2&trip_hash={tripId}."""
    return _get_json(f"{REPORT_API}/trip-details", {"v": "2", "trip_hash": trip_id_b36}, session)
