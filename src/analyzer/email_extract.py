"""Extracción de email desde HTML descargado, con fallback ficticio.

Si la web del negocio existe se intenta localizar el primer email "humano" que
aparezca en el HTML (mailto: o texto plano). Si no se encuentra ninguno, se
genera una dirección ficticia `vmarketing@<slug>.com` donde `<slug>` es el
nombre del negocio normalizado a ASCII y sin caracteres no válidos en emails.
"""
from __future__ import annotations

import re
from typing import Optional

from unidecode import unidecode

# Patrón pragmático para localizar emails en HTML. No pretende ser RFC 5322
# completo — sólo capturar el formato común que aparece en webs de pymes.
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9](?:[a-zA-Z0-9._+\-]*[a-zA-Z0-9])?"
    r"@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?"
    r"\.[a-zA-Z]{2,}"
)

# Extensiones de fichero que delatan falsos positivos como `logo@2x.png`
_FILE_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "ico",
    "css", "js", "pdf", "woff", "woff2", "ttf", "eot",
}

# Local-parts genéricos que no son útiles como contacto comercial real
_BLOCKED_LOCALS = {"sentry", "noreply", "no-reply", "do-not-reply"}

# Dominios SaaS/CDN/tracking que aparecen pseudo-emails en HTML pero no son
# direcciones de contacto reales (Sentry DSN, Stripe webhooks, etc.)
_BLOCKED_DOMAINS = {"sentry.io", "ingest.sentry.io", "sentry-next.wixpress.com"}

_SLUG_INVALID_RE = re.compile(r"[^a-z0-9]+")


def extract_email_from_html(html: Optional[str]) -> Optional[str]:
    """Devuelve el primer email "humano" encontrado en el HTML, o None."""
    if not html:
        return None
    for match in _EMAIL_RE.finditer(html):
        candidate = match.group(0)
        local, _, domain = candidate.rpartition("@")
        ext = domain.rsplit(".", 1)[-1].lower()
        if ext in _FILE_EXTENSIONS:
            continue
        if local.replace(".", "").replace("-", "").replace("_", "").isdigit():
            continue
        if local.lower() in _BLOCKED_LOCALS:
            continue
        if domain.lower() in _BLOCKED_DOMAINS:
            continue
        return candidate
    return None


def _slugify_business(name: str) -> str:
    """Convierte un nombre de negocio en un slug seguro para email.
    Ej: "Joyería Águila & Co. (Vigo)" -> "joyeriaaguilacovigo"."""
    if not name or not name.strip():
        return "negocio"
    s = unidecode(name).lower().strip()
    s = _SLUG_INVALID_RE.sub("", s)
    return s or "negocio"


def fictitious_email(business_name: str) -> str:
    return f"vmarketing@{_slugify_business(business_name)}.com"


def get_email(html: Optional[str], business_name: str) -> str:
    """Devuelve el primer email real encontrado en el HTML; si no, uno ficticio."""
    real = extract_email_from_html(html)
    if real:
        return real
    return fictitious_email(business_name)
