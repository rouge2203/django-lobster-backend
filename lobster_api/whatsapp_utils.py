import re
import requests
import environ

env = environ.Env()

WHATSAPP_PHONE_NUMBER_ID = env('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_ACCESS_TOKEN = env('WHATSAPP_ACCESS_TOKEN')

WA_API_URL = f"https://graph.facebook.com/v22.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
WA_HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def normalize_phone(raw):
    """
    Strip all non-digit characters from a phone string.
    If the result is 8 digits (Costa Rica local), prepend country code 506.
    """
    digits = re.sub(r'\D', '', raw)
    if len(digits) == 8:
        digits = '506' + digits
    return digits


def send_whatsapp_text(to, body):
    """Send a plain text WhatsApp message via the Cloud API."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    return requests.post(WA_API_URL, json=payload, headers=WA_HEADERS)


def send_whatsapp_interactive_buttons(to, body_text, buttons):
    """Send an interactive button message (up to 3 buttons)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                    for b in buttons
                ]
            },
        },
    }
    return requests.post(WA_API_URL, json=payload, headers=WA_HEADERS)


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
    return requests.post(WA_API_URL, json=payload, headers=WA_HEADERS)
