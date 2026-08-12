import re
import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

META_HOST = "graph.facebook.com"


def normalize_phone(raw):
    """
    Strip all non-digit characters from a phone string.
    If the result is 8 digits (Costa Rica local), prepend country code 506.
    """
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 8:
        digits = '506' + digits
    return digits


_route_logged = False


def _get_api_url():
    # Announce the resolved host once per process. Sending works against both
    # Meta and the relay, so the logs are the only way to tell them apart.
    global _route_logged
    base_url = settings.WHATSAPP_API_BASE_URL

    # An env var that exists but is blank does NOT fall back to the default:
    # django-environ only uses the default when the key is absent entirely. A
    # blank value would otherwise build a schemeless URL and surface as an
    # opaque requests.MissingSchema deep inside the send.
    if not base_url.startswith(("http://", "https://")):
        raise ImproperlyConfigured(
            f"WHATSAPP_API_BASE_URL is '{base_url}', which is not a full URL. Set it to "
            f"https://api.dualhook.com (relay) or https://{META_HOST} (direct). Note that "
            f"leaving it blank is not the same as leaving it unset."
        )

    if not _route_logged:
        route = "META DIRECT" if META_HOST in base_url else "DUALHOOK RELAY"
        print(f"[WhatsApp] Outbound route: {route} → {base_url}/{settings.WHATSAPP_API_VERSION}")
        _route_logged = True

    return (
        f"{base_url}/{settings.WHATSAPP_API_VERSION}"
        f"/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )


def _get_headers():
    """
    Build the auth headers, refusing to send a Meta-issued credential anywhere
    but Meta. A token starting with EAA is only valid at graph.facebook.com, so
    if the base URL points at a relay the credential must be that relay's own
    key (Dualhook issues dh_live_...). Failing here is deliberate: the request
    would be rejected downstream anyway, and this way the token never leaves us.
    """
    token = settings.WHATSAPP_ACCESS_TOKEN
    base_url = settings.WHATSAPP_API_BASE_URL

    if token.startswith("EAA") and META_HOST not in base_url:
        raise ImproperlyConfigured(
            f"WHATSAPP_ACCESS_TOKEN is a Meta token but WHATSAPP_API_BASE_URL is "
            f"'{base_url}'. Set the relay's own key (dh_live_...) before moving the "
            f"host, or point WHATSAPP_API_BASE_URL back at https://{META_HOST}."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def send_whatsapp_text(to, body):
    """Send a plain text WhatsApp message via the Cloud API."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    return requests.post(_get_api_url(), json=payload, headers=_get_headers())


def send_whatsapp_interactive_buttons(to, body_text, buttons, footer_text=None):
    """Send an interactive button message (up to 3 buttons)."""
    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons
            ]
        },
    }
    if footer_text:
        interactive["footer"] = {"text": footer_text}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    return requests.post(_get_api_url(), json=payload, headers=_get_headers())


def send_whatsapp_cta_url(to, body_text, footer_text, button_text, url):
    """Send an interactive CTA URL message with a clickable link button."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": body_text},
            "footer": {"text": footer_text},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": button_text,
                    "url": url,
                },
            },
        },
    }
    return requests.post(_get_api_url(), json=payload, headers=_get_headers())


def send_whatsapp_template(to, template_name, language_code, components):
    """Send a pre-approved WhatsApp template message."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components,
        },
    }
    return requests.post(_get_api_url(), json=payload, headers=_get_headers())
