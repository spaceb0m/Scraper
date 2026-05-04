from __future__ import annotations

from src.analyzer.email_extract import (
    extract_email_from_html,
    fictitious_email,
    get_email,
)


# ─── Extracción real ────────────────────────────────────────────────────

def test_extract_mailto_link():
    html = '<html><a href="mailto:info@example.com">Contacto</a></html>'
    assert extract_email_from_html(html) == "info@example.com"


def test_extract_plain_text_email():
    html = "<p>Escríbenos a contacto@negocio.es para info</p>"
    assert extract_email_from_html(html) == "contacto@negocio.es"


def test_extract_first_when_multiple():
    html = "Contacta info@a.com o ventas@b.com"
    assert extract_email_from_html(html) == "info@a.com"


def test_extract_ignores_image_filenames():
    html = '<img src="logo@2x.png" />'
    assert extract_email_from_html(html) is None


def test_extract_ignores_woff_filenames():
    html = '<link href="font@1x.woff2" />'
    assert extract_email_from_html(html) is None


def test_extract_ignores_sentry_dsn():
    html = "Sentry.init({ dsn: 'https://abc@sentry.io/1234' });"
    # `abc@sentry.io` no termina en TLD válido para nuestro regex (sin .ext final),
    # pero el local 'sentry' también está bloqueado por seguridad.
    result = extract_email_from_html(html)
    assert result is None or "sentry" not in result.lower()


def test_extract_ignores_noreply():
    html = "noreply@example.com es nuestro automático"
    assert extract_email_from_html(html) is None


def test_extract_returns_real_after_blocked():
    html = "noreply@example.com pero contacta a hola@example.com"
    assert extract_email_from_html(html) == "hola@example.com"


def test_extract_empty_inputs():
    assert extract_email_from_html("") is None
    assert extract_email_from_html(None) is None


# ─── Email ficticio ─────────────────────────────────────────────────────

def test_fictitious_basic():
    assert fictitious_email("Boutique Lolita") == "vmarketing@boutiquelolita.com"


def test_fictitious_strips_accents_and_punctuation():
    assert fictitious_email("Joyería Águila & Co. (Vigo)") == "vmarketing@joyeriaaguilacovigo.com"


def test_fictitious_handles_spaces_and_dashes():
    assert fictitious_email("La Tienda - de - María") == "vmarketing@latiendademaria.com"


def test_fictitious_empty():
    assert fictitious_email("") == "vmarketing@negocio.com"
    assert fictitious_email("   ") == "vmarketing@negocio.com"


def test_fictitious_only_punctuation():
    assert fictitious_email("---!!---") == "vmarketing@negocio.com"


# ─── get_email (combinación) ────────────────────────────────────────────

def test_get_email_prefers_real():
    html = "contacta a contacto@real.com hoy"
    assert get_email(html, "Boutique X") == "contacto@real.com"


def test_get_email_falls_back_to_fictitious():
    assert get_email("", "Boutique X") == "vmarketing@boutiquex.com"
    assert get_email(None, "Boutique X") == "vmarketing@boutiquex.com"


def test_get_email_html_without_email_uses_fallback():
    html = "<html><body>Sin contacto aquí</body></html>"
    assert get_email(html, "Tienda Y") == "vmarketing@tienday.com"
