import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .supabase_client import get_supabase_client
from .tellos_views import send_cancellation_admin_notification
from .whatsapp_utils import (
    normalize_phone,
    send_whatsapp_text,
    send_whatsapp_interactive_buttons,
    send_whatsapp_cta_url,
)

COSTA_RICA_TZ = ZoneInfo('America/Costa_Rica')

MESES_ESPANOL = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_reservation_by_phone(phone):
    """
    Legacy fallback: find the soonest pending upcoming reservation whose WhatsApp
    reminder was already sent and whose celular_reserva matches the incoming phone
    (after normalization). Only used when the incoming button payload does not
    carry an explicit reserva id (i.e. messages sent before the payload-based flow).
    Returns (reserva_dict, cancha_dict) or (None, None).
    """
    supabase = get_supabase_client()
    normalized = normalize_phone(phone)

    now_str = datetime.now(timezone.utc).astimezone(COSTA_RICA_TZ).strftime('%Y-%m-%d %H:%M:%S')

    response = supabase.table('reservas').select('*, canchas(nombre, local, cantidad)') \
        .eq('whatsapp_enviado', True) \
        .is_('whatsapp_confirmada', 'null') \
        .not_.is_('celular_reserva', 'null') \
        .gte('hora_inicio', now_str) \
        .order('hora_inicio') \
        .execute()

    for reserva in response.data:
        if normalize_phone(reserva['celular_reserva']) == normalized:
            cancha = reserva.pop('canchas', None)
            return reserva, cancha

    return None, None


def find_reservation_by_id(reserva_id):
    """
    Look up a reservation by its UUID, joining cancha info.
    Returns (reserva_dict, cancha_dict) or (None, None).
    """
    supabase = get_supabase_client()

    response = supabase.table('reservas').select('*, canchas(nombre, local, cantidad)') \
        .eq('id', reserva_id) \
        .limit(1) \
        .execute()

    if not response.data:
        return None, None

    reserva = response.data[0]
    cancha = reserva.pop('canchas', None)
    return reserva, cancha


def format_reserva_details(reserva, cancha):
    """Return (fecha, hora, cancha_name, local_nombre) strings for WhatsApp messages."""
    hora_inicio = reserva['hora_inicio']
    try:
        dt = datetime.strptime(hora_inicio, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        dt = datetime.fromisoformat(hora_inicio.replace('Z', '+00:00'))

    fecha = f"{dt.day} de {MESES_ESPANOL[dt.month]}"
    hora_str = dt.strftime('%I:%M').lstrip('0')
    periodo = 'A.M.' if dt.hour < 12 else 'P.M.'
    hora = f"{hora_str} {periodo}"

    cantidad = cancha.get('cantidad', '5')
    cancha_name = f"{cancha['nombre']} (Fut {cantidad})"
    local_nombre = 'La Sabana' if cancha['local'] == 1 else 'El Carmen de Guadalupe'

    return fecha, hora, cancha_name, local_nombre


def has_payment(reserva):
    """Check if the reservation has any payment recorded."""
    return bool(reserva.get('sinpe_reserva')) or reserva.get('pago_checkeado') is True


# ---------------------------------------------------------------------------
# Button handlers
# ---------------------------------------------------------------------------

def handle_button_tap(phone, msg):
    """Handle template quick-reply buttons: Confirmar / Cancelar.

    New messages carry payloads like CONFIRM_REMINDER_<uuid> / CANCEL_REMINDER_<uuid>
    so we can act on the exact reserva. Legacy messages (sent before the payload
    flow) only carry the button text; in that case we fall back to the soonest
    pending reserva for this phone.
    """
    button_text = msg["button"]["text"]
    button_payload = msg["button"].get("payload", "") or ""

    intent = None
    reserva = None
    cancha = None

    if button_payload.startswith("CONFIRM_REMINDER_"):
        intent = "confirm"
        reserva_id = button_payload[len("CONFIRM_REMINDER_"):]
        reserva, cancha = find_reservation_by_id(reserva_id)
    elif button_payload.startswith("CANCEL_REMINDER_"):
        intent = "cancel"
        reserva_id = button_payload[len("CANCEL_REMINDER_"):]
        reserva, cancha = find_reservation_by_id(reserva_id)
    else:
        if button_text == "Confirmar":
            intent = "confirm"
        elif button_text == "Cancelar":
            intent = "cancel"
        reserva, cancha = find_reservation_by_phone(phone)

    if intent is None:
        return

    if not reserva:
        send_whatsapp_text(
            phone,
            "No encontramos una reservación pendiente asociada a este número. ❌"
        )
        return

    if reserva.get('whatsapp_confirmada') is not None:
        send_whatsapp_text(
            phone,
            "Su reservación ya fue confirmada. ✅ Si desea cancelar, escríbanos por este medio.\n\n"
            "Puede hacer otra reservación en futboltello.com ⚽️"
        )
        return

    supabase = get_supabase_client()

    if intent == "confirm":
        supabase.table('reservas').update({
            'whatsapp_confirmada': True
        }).eq('id', reserva['id']).execute()

        reserva_url = f"https://futboltello.com/reserva/{reserva['id']}"

        if has_payment(reserva):
            body = (
                "¡Reservación confirmada! ✅\n\n"
                f"Puede ver detalles de su reservación y cómo llegar a nuestras instalaciones al clic en el botón de abajo.\n\n"
                "Les esperamos 👋🏻"
            )
            cta_button_text = "Ver reservación"
        else:
            body = (
                "¡Reservación confirmada! ✅\n\n"
                "*Recuerde hacer un adelanto del 50% del valor de la cancha con su nombre como detalle y subir el comprobante en el link de abajo "
                "o su reservación podría ser cancelada.* ‼️\n\n"
                "Les esperamos 👋🏻"
            )
            cta_button_text = "Subir comprobante"
        send_whatsapp_cta_url(phone, body, "Un abrazo de gol", cta_button_text, reserva_url)

    elif intent == "cancel":
        fecha, hora, cancha_name, local_nombre = format_reserva_details(reserva, cancha)

        body = (
            f"¿Está seguro/a que desea cancelar su reservación?\n\n"
            f"📆 {fecha}\n"
            f"🕑 {hora}\n"
            f"🏟️ {cancha_name}\n"
            f"📍 {local_nombre}\n"
        )
        send_whatsapp_interactive_buttons(
            phone,
            body,
            [
                {"id": f"CONFIRM_CANCEL_{reserva['id']}", "title": "Sí, cancelar"},
                {"id": f"CONFIRM_RESERVA_{reserva['id']}", "title": "Confirmar reserva"},
            ],
        )


def handle_interactive_tap(phone, msg):
    """Handle interactive button taps: Sí cancelar / Confirmar reserva.

    New ids look like CONFIRM_CANCEL_<uuid> / CONFIRM_RESERVA_<uuid> so we can
    act on the exact reserva. Plain CONFIRM_CANCEL / CONFIRM_RESERVA ids come
    from messages sent before the id-based flow and fall back to the soonest
    pending reserva for this phone.
    """
    button_id = msg["interactive"]["button_reply"]["id"]

    intent = None
    reserva = None
    cancha = None

    if button_id.startswith("CONFIRM_CANCEL_"):
        intent = "cancel"
        reserva_id = button_id[len("CONFIRM_CANCEL_"):]
        reserva, cancha = find_reservation_by_id(reserva_id)
    elif button_id.startswith("CONFIRM_RESERVA_"):
        intent = "confirm"
        reserva_id = button_id[len("CONFIRM_RESERVA_"):]
        reserva, cancha = find_reservation_by_id(reserva_id)
    elif button_id == "CONFIRM_CANCEL":
        intent = "cancel"
        reserva, cancha = find_reservation_by_phone(phone)
    elif button_id == "CONFIRM_RESERVA":
        intent = "confirm"
        reserva, cancha = find_reservation_by_phone(phone)

    if intent is None:
        return

    if not reserva:
        send_whatsapp_text(
            phone,
            "No encontramos una reservación pendiente asociada a este número ❌.\n\n"
            "Puede hacer una nueva reservación en futboltello.com ⚽️"
        )
        return

    if reserva.get('whatsapp_confirmada') is not None:
        send_whatsapp_text(
            phone,
            "Su reservación ya ha sido procesada.\n\n"
            "Puede hacer otra reservación en futboltello.com ⚽️"
        )
        return

    supabase = get_supabase_client()

    if intent == "cancel":
        supabase.table('reservas').delete().eq('id', reserva['id']).execute()

        # Notify admins by email that the client cancelled via WhatsApp.
        # We do this AFTER the delete succeeds so we don't email about a slot
        # that wasn't actually freed. Email failures are swallowed inside the
        # helper so they never break the WhatsApp UX.
        try:
            send_cancellation_admin_notification(reserva, cancha, cancelled_by='whatsapp')
        except Exception as e:
            print(f"[WhatsApp Webhook] Failed to send cancellation admin email: {e}")

        send_whatsapp_text(
            phone,
            "Reservación cancelada ❌.\n\n"
            "Puede hacer una nueva reservación cuando guste en: futboltello.com ⚽️"
        )

    elif intent == "confirm":
        supabase.table('reservas').update({
            'whatsapp_confirmada': True
        }).eq('id', reserva['id']).execute()

        reserva_url = f"https://futboltello.com/reserva/{reserva['id']}"
        if has_payment(reserva):
            body = (
                "¡Reservación confirmada! ✅\n\n"
                f"Puede ver detalles de su reservación y cómo llegar a nuestras instalaciones al clic en el botón de abajo. \n\n"
                "Les esperamos 👋🏻"
            )
            cta_button_text = "Ver reservación"
        else:
            body = (
                "¡Reservación confirmada! ✅\n\n"
                "*Recuerde hacer un adelanto del 50% del valor de la cancha con su nombre como detalle y subir el comprobante en el link de abajo "
                "o su reservación podría ser cancelada.* ‼️\n\n"
                "Les esperamos 👋🏻"
            )
            cta_button_text = "Subir comprobante"
        send_whatsapp_cta_url(phone, body, "Un abrazo de gol", cta_button_text, reserva_url)


# ---------------------------------------------------------------------------
# Main webhook view
# ---------------------------------------------------------------------------

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.DUALHOOK_TOKEN:
            return HttpResponse(challenge, status=200)
        return HttpResponse("Forbidden", status=403)

    if request.method == "POST":
        body = json.loads(request.body)
        print(f"[WhatsApp Webhook] Incoming payload: {json.dumps(body, indent=2)}")

        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})

        statuses = value.get("statuses", [])
        for status in statuses:
            print(f"[WhatsApp Webhook] STATUS UPDATE: "
                  f"recipient={status.get('recipient_id')} "
                  f"status={status.get('status')} "
                  f"timestamp={status.get('timestamp')} "
                  f"errors={status.get('errors', 'none')}")

        messages = value.get("messages", [])
        for msg in messages:
            phone = msg["from"]
            print(f"[WhatsApp Webhook] MESSAGE: type={msg['type']} from={phone}")

            if msg["type"] == "button":
                handle_button_tap(phone, msg)

            elif msg["type"] == "interactive":
                handle_interactive_tap(phone, msg)

            elif msg["type"] == "text":
                pass

        return JsonResponse({"status": "ok"}, status=200)
