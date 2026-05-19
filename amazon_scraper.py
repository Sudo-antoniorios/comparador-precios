"""Búsqueda de precios en Amazon España.

Estrategia: petición HTTP directa con headers de navegador real.
Si Amazon bloquea (503, captcha, etc.) se devuelve "No encontrado"
de forma elegante en lugar de romper la aplicación.
"""

import random
import re
import time

import requests
from bs4 import BeautifulSoup

# Varios User-Agents reales para rotar y reducir el riesgo de bloqueo.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

PRICE_NOT_FOUND = "No encontrado"
PRICE_BLOCKED = "Amazon bloqueó la petición (503)"


def _build_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def _extract_first_price(html):
    """Devuelve el primer precio relevante del HTML de resultados, o None."""
    soup = BeautifulSoup(html, "html.parser")

    # 1) Precio dentro de un resultado de búsqueda real.
    results = soup.select("div[data-component-type='s-search-result']")
    for result in results:
        offscreen = result.select_one("span.a-price > span.a-offscreen")
        if offscreen and offscreen.get_text(strip=True):
            return offscreen.get_text(strip=True)
        whole = result.select_one("span.a-price-whole")
        if whole and whole.get_text(strip=True):
            frac = result.select_one("span.a-price-fraction")
            frac_txt = frac.get_text(strip=True) if frac else "00"
            return f"{whole.get_text(strip=True)}{frac_txt} €"

    # 2) Fallback: cualquier precio offscreen de la página.
    any_price = soup.select_one("span.a-price > span.a-offscreen")
    if any_price and any_price.get_text(strip=True):
        return any_price.get_text(strip=True)

    return None


def _looks_blocked(html):
    lowered = html.lower()
    markers = [
        "api-services-support@amazon",
        "to discuss automated access",
        "captcha",
        "robot check",
        "lo sentimos, algo ha ido mal",
    ]
    return any(m in lowered for m in markers)


def buscar_precio_amazon(ean, max_reintentos=2, pausa=1.5):
    """Busca un EAN en Amazon.es y devuelve el primer precio encontrado.

    Nunca lanza excepción: ante cualquier fallo devuelve un texto legible.
    """
    ean = str(ean).strip()
    if not ean:
        return PRICE_NOT_FOUND

    url = f"https://www.amazon.es/s?k={ean}"

    for intento in range(max_reintentos + 1):
        try:
            resp = requests.get(url, headers=_build_headers(), timeout=15)
        except requests.RequestException:
            time.sleep(pausa)
            continue

        if resp.status_code == 503:
            time.sleep(pausa * (intento + 1))
            continue

        if resp.status_code != 200:
            time.sleep(pausa)
            continue

        if _looks_blocked(resp.text):
            time.sleep(pausa * (intento + 1))
            continue

        precio = _extract_first_price(resp.text)
        if precio:
            return precio
        return PRICE_NOT_FOUND

    return PRICE_BLOCKED
