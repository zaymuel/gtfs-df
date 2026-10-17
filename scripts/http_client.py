"""
http_client.py - Cliente HTTP polido e resiliente, compartilhado por DFTrans e Bus2.

Política (Ticket 03):
  * uma ``requests.Session`` por thread (thread-safe);
  * pausa de ``delay`` segundos após cada requisição, por worker;
  * backoff exponencial com jitter em HTTP 429/5xx e erros de rede/timeout
    (``backoff * 2**(tentativa-1)``; respeita ``Retry-After`` quando presente);
  * HTTP 404/204 => ``None`` (recurso inexistente). Falhas persistentes => ``HttpRequestError``,
    para que o chamador diferencie "não existe" de "falhou" (e não grave cache corrompido).
"""

import config
import random
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class HttpRequestError(RuntimeError):
    """Falha persistente (rede, timeout, 429/5xx esgotando retries, JSON inválido)."""


class PoliteClient:
    def __init__(self,
                 base_url: str = "",
                 delay: float = config.HTTP_DELAY_SEC,
                 retries: int = config.HTTP_RETRIES,
                 backoff: float = config.HTTP_BACKOFF_SEC,
                 timeout: float = config.HTTP_TIMEOUT_SEC,
                 headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip("/")
        self.delay = delay
        self.retries = max(1, retries)
        self.backoff = backoff
        self.timeout = timeout
        self.headers = dict(headers or config.HTTP_HEADERS)
        self._local = threading.local()
        self._counter_lock = threading.Lock()
        self.request_count = 0
        self.retry_count = 0

    # -- infraestrutura ------------------------------------------------------
    @property
    def session(self) -> requests.Session:
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(self.headers)
            self._local.session = s
        return s

    def _bump(self, attr: str) -> None:
        with self._counter_lock:
            setattr(self, attr, getattr(self, attr) + 1)

    def _sleep_backoff(self, attempt: int, retry_after: Optional[str] = None) -> None:
        if retry_after:
            try:
                delay = float(retry_after)
            except ValueError:
                delay = self.backoff * (2 ** (attempt - 1))
        else:
            delay = self.backoff * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, 0.5)
        time.sleep(delay + jitter)

    # -- operações públicas --------------------------------------------------
    def get_response(self, url_or_path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Executa requisição GET com retries automáticos, backoff exponencial e jitter.
        Retorna o objeto requests.Response preservando status_code, url, headers e text.
        """
        url = url_or_path if url_or_path.startswith(
            "http") else f"{self.base_url}/{url_or_path.lstrip('/')}"
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.retries + 1):
            self._bump("request_count")
            try:
                resp = self.session.get(
                    url, params=params, timeout=self.timeout)
                if resp.status_code == 200:
                    time.sleep(self.delay)
                    return resp
                if resp.status_code in (404, 204):
                    time.sleep(self.delay)
                    return resp
                if resp.status_code in (429, 500, 502, 503, 504):
                    self._bump("retry_count")
                    if attempt == self.retries:
                        raise HttpRequestError(
                            f"HTTP {resp.status_code} em {url} após {self.retries} tentativas")
                    self._sleep_backoff(
                        attempt, resp.headers.get("Retry-After"))
                    continue
                resp.raise_for_status()
                return resp
            except (requests.exceptions.RequestException, ValueError) as exc:
                self._bump("retry_count")
                last_exc = exc
                if attempt == self.retries:
                    break
                self._sleep_backoff(attempt)

        raise HttpRequestError(
            f"Falha definitiva ao consultar {url}: {last_exc}")

    def get_json(self, url_or_path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Obtém payload JSON de um endpoint. Retorna None para HTTP 404/204."""
        resp = self.get_response(url_or_path, params=params)
        if resp.status_code in (404, 204):
            return None
        return resp.json()
