from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail, EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.decorators import api_view
from datetime import datetime
import json

# Admin emails for notifications (all admins receive new-reservation, reto and
# cancellation notifications)
ADMIN_EMAILS = [
    'Agendakathia74@gmail.com',
    'aruiz@lobsterlabs.net',
]

# Human labels for the `source` field accepted by /tellos/confirm-reservation.
# Anything not in this map falls back to the default 'web' label.
SOURCE_LABELS = {
    'public': 'Cliente vía web',
    'admin': 'Administrador',
    'web': 'Cliente vía web',
}


def get_tellos_connection():
    """Create and return a connection using tellos email settings."""
    return get_connection(
        backend=settings.TELLOS_EMAIL_BACKEND,
        host=settings.TELLOS_EMAIL_HOST,
        port=settings.TELLOS_EMAIL_PORT,
        username=settings.TELLOS_EMAIL_HOST_USER,
        password=settings.TELLOS_EMAIL_HOST_PASSWORD,
        use_tls=settings.TELLOS_EMAIL_USE_TLS,
        use_ssl=settings.TELLOS_EMAIL_USE_SSL,
    )


def send_admin_notification(context, connection=None):
    """
    Send admin notification email about new reservation.
    Uses the same context as the user confirmation email.
    Optionally accepts an existing connection to reuse.

    Expects context to include `source` ('public' / 'admin' / 'web') so the
    subject line and template can reflect where the reservation came from.
    `created_by_name` / `created_by_email` are optional and only rendered when
    present (typically for admin-created reservations).
    """
    try:
        tellos_connection = connection if connection else get_tellos_connection()

        source = (context.get('source') or 'web').lower()
        source_label = SOURCE_LABELS.get(source, 'Cliente vía web')
        context.setdefault('source', source)
        context.setdefault('source_label', source_label)

        # Subject prefix tells admins at a glance who created it
        if source == 'admin':
            subject_prefix = 'Nueva Reserva (Admin)'
        else:
            subject_prefix = 'Nueva Reserva (Web)'
        subject = f"{subject_prefix}: {context['cancha_nombre']}, {context['hora']}"

        html_content = render_to_string('email_templates/tellos/admin_reservation_notification.html', context)

        creator_line = ''
        if context.get('created_by_name'):
            creator_line = f"\n        Creada por: {context['created_by_name']}"
            if context.get('created_by_email'):
                creator_line += f" ({context['created_by_email']})"

        text_content = f"""Nueva Reservación Recibida

        Origen: {source_label}{creator_line}

        Cliente: {context['nombre_reserva']}
        Teléfono: {context['celular_reserva']}
        Correo: {context.get('correo_reserva') or '—'}

        Cancha: {context['cancha_nombre']}
        Local: {context['local_nombre']}
        Fecha: {context['fecha']} — {context['hora']}
        Jugadores: {context['jugadores']}
        Árbitro: {context['arbitro']}
        Total: ₡{context['precio_total']}

        Ver reservación: {context['reserva_url']}
        ID de reservación: {context['reserva_id']}
        """

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
            to=ADMIN_EMAILS,
            connection=tellos_connection
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f"Admin notification email sent successfully to: {ADMIN_EMAILS}")
        return True
    except Exception as e:
        print(f"Error sending admin notification email: {str(e)}")
        return False


def send_cancellation_admin_notification(reserva, cancha, cancelled_by='whatsapp', connection=None):
    """
    Notify admins that a reservation was cancelled. Currently only fired from the
    WhatsApp webhook when a client cancels through the bot.

    `reserva` and `cancha` are dicts as returned by the supabase select used in
    tellos_whatsapp_views.find_reservation_by_id (i.e. cancha already split off
    from the joined row). Returns True on success.
    """
    try:
        tellos_connection = connection if connection else get_tellos_connection()

        hora_inicio_raw = reserva.get('hora_inicio')
        hora_fin_raw = reserva.get('hora_fin')

        # hora_inicio comes back as 'YYYY-MM-DD HH:MM:SS' from Supabase; fall back
        # to fromisoformat so we don't crash if Supabase ever returns an ISO 8601
        # string with a 'T' separator.
        def _parse(ts):
            if not ts:
                return None
            try:
                return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))

        inicio_dt = _parse(hora_inicio_raw)
        fin_dt = _parse(hora_fin_raw)

        meses_espanol = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }

        if inicio_dt:
            fecha = f"{inicio_dt.day} de {meses_espanol[inicio_dt.month]} de {inicio_dt.year}"
            hi = inicio_dt.strftime('%I:%M').lstrip('0')
            periodo_inicio = 'AM' if inicio_dt.hour < 12 else 'PM'
            if fin_dt:
                hf = fin_dt.strftime('%I:%M').lstrip('0')
                periodo_fin = 'AM' if fin_dt.hour < 12 else 'PM'
                hora = f"{hi} {periodo_inicio} - {hf} {periodo_fin}"
            else:
                hora = f"{hi} {periodo_inicio}"
        else:
            fecha = '—'
            hora = '—'

        cancha = cancha or {}
        local_id = cancha.get('local')
        local_nombre = 'La Sabana' if local_id == 1 else 'El Carmen de Guadalupe' if local_id == 2 else '—'
        cantidad = cancha.get('cantidad') or '5'
        cancha_nombre = cancha.get('nombre') or '—'
        cancha_full = f"{cancha_nombre} (Fut {cantidad})" if cancha.get('nombre') else cancha_nombre

        precio_value = reserva.get('precio') or 0
        try:
            precio_total = f"{int(precio_value):,}".replace(',', '.')
        except (TypeError, ValueError):
            precio_total = str(precio_value)

        # Capture the cancellation moment in Costa Rica time for the admin email
        from zoneinfo import ZoneInfo
        cancelled_at = datetime.now(ZoneInfo('America/Costa_Rica')).strftime('%d/%m/%Y %I:%M %p')

        cancellation_source_labels = {
            'whatsapp': 'Cliente vía WhatsApp',
        }
        cancellation_source_label = cancellation_source_labels.get(
            cancelled_by, cancelled_by.capitalize() if cancelled_by else 'Desconocido'
        )

        context = {
            'nombre_reserva': reserva.get('nombre_reserva') or '—',
            'celular_reserva': reserva.get('celular_reserva') or '—',
            'correo_reserva': reserva.get('correo_reserva') or '—',
            'cancha_nombre': cancha_full,
            'local_nombre': local_nombre,
            'local_id': local_id,
            'fecha': fecha,
            'hora': hora,
            'arbitro': 'Sí' if reserva.get('arbitro') else 'No',
            'precio_total': precio_total,
            'reserva_id': reserva.get('id') or '—',
            'cancelled_by': cancelled_by,
            'cancelled_by_label': cancellation_source_label,
            'cancelled_at': cancelled_at,
        }

        subject = f"Reserva CANCELADA: {cancha_full}, {hora}"

        html_content = render_to_string(
            'email_templates/tellos/admin_reservation_cancelled.html', context
        )

        text_content = f"""Reservación Cancelada

        Cancelada por: {cancellation_source_label}
        Cuándo se canceló: {cancelled_at} (Costa Rica)

        Cliente: {context['nombre_reserva']}
        Teléfono: {context['celular_reserva']}
        Correo: {context['correo_reserva']}

        Cancha: {context['cancha_nombre']}
        Local: {context['local_nombre']}
        Fecha: {context['fecha']} — {context['hora']}
        Árbitro: {context['arbitro']}
        Total: ₡{context['precio_total']}

        ID de reservación: {context['reserva_id']}
        """

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
            to=ADMIN_EMAILS,
            connection=tellos_connection
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f"Admin cancellation email sent successfully to: {ADMIN_EMAILS}")
        return True
    except Exception as e:
        print(f"Error sending admin cancellation email: {str(e)}")
        return False


@api_view(['POST'])
def confirm_reservation(request):
    try:
        # Parse JSON data from request body
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
        
        # Required fields. NOTE: correo_reserva is intentionally NOT required —
        # the frontend always calls this endpoint so admins get notified, but
        # not every client provides an email. When it's missing we just skip
        # the user-facing confirmation email and only send the admin one.
        required_fields = [
            'reserva_id', 'hora_inicio', 'hora_fin', 'cancha_id',
            'cancha_nombre', 'cancha_local', 'nombre_reserva',
            'celular_reserva', 'precio',
            'arbitro', 'jugadores', 'reserva_url'
        ]

        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return JsonResponse({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)

        reserva_id = data['reserva_id']
        hora_inicio = data['hora_inicio']
        hora_fin = data['hora_fin']
        cancha_id = data['cancha_id']
        cancha_nombre = data['cancha_nombre']
        cancha_local = data['cancha_local']
        nombre_reserva = data['nombre_reserva']
        celular_reserva = data['celular_reserva']
        correo_reserva = (data.get('correo_reserva') or '').strip()
        precio = data['precio']
        arbitro = data['arbitro']
        jugadores = data['jugadores']
        reserva_url = data['reserva_url']

        # Optional metadata about who/where the reservation came from
        source = (data.get('source') or 'public').lower()
        created_by_name = (data.get('created_by_name') or '').strip()
        created_by_email = (data.get('created_by_email') or '').strip()
        
        # Parse datetime strings
        try:
            inicio_dt = datetime.strptime(hora_inicio, '%Y-%m-%d %H:%M:%S')
            fin_dt = datetime.strptime(hora_fin, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return JsonResponse({
                'error': 'Invalid datetime format. Expected format: YYYY-MM-DD HH:MM:SS'
            }, status=400)
        
        # Format date and time for display (Spanish format)
        # Spanish month names mapping
        meses_espanol = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        fecha = f"{inicio_dt.day} de {meses_espanol[inicio_dt.month]} de {inicio_dt.year}"
        
        # Format time (convert to 12-hour format with Spanish AM/PM)
        hora_inicio_str = inicio_dt.strftime('%I:%M').lstrip('0')
        hora_fin_str = fin_dt.strftime('%I:%M').lstrip('0')
        periodo_inicio = 'AM' if inicio_dt.hour < 12 else 'PM'
        periodo_fin = 'AM' if fin_dt.hour < 12 else 'PM'
        hora = f"{hora_inicio_str} {periodo_inicio} - {hora_fin_str} {periodo_fin}"
        
        # Determine local name
        local_nombre = 'La Sabana' if cancha_local == 1 else 'El Carmen de Guadalupe'
        
        # Format arbitro text
        arbitro_text = 'Sí' if arbitro else 'No'
        
        # Format price with colones symbol
        precio_total = f"{precio:,}".replace(',', '.')
        
        context = {
            'nombre_reserva': nombre_reserva,
            'celular_reserva': celular_reserva,
            'correo_reserva': correo_reserva,
            'cancha_nombre': cancha_nombre,
            'local_nombre': local_nombre,
            'local_id': cancha_local,
            'fecha': fecha,
            'hora': hora,
            'jugadores': jugadores,
            'arbitro': arbitro_text,
            'precio_total': precio_total,
            'reserva_id': reserva_id,
            'reserva_url': reserva_url,
            # Source / creator metadata used by the admin notification template
            'source': source,
            'source_label': SOURCE_LABELS.get(source, 'Cliente vía web'),
            'created_by_name': created_by_name,
            'created_by_email': created_by_email,
        }
        
        subject = f"Futbol Tello: Reservación confirmada"
        
        # Send confirmation email to user and admin using same connection
        email_sent = False
        admin_email_sent = False
        
        # Create a single connection and reuse for both emails (faster)
        tellos_connection = get_tellos_connection()
        
        try:
            tellos_connection.open()

            # User-facing confirmation only goes out if the client provided an
            # email; otherwise we silently skip and still notify admins below.
            if correo_reserva:
                html_content = render_to_string(
                    'email_templates/tellos/reservation_confirmation.html', context
                )

                text_content = f"""¡Reserva confirmada!

            Hola {nombre_reserva}, tu reserva ya está registrada.

            Cancha: {cancha_nombre}
            Local: {local_nombre}
            Fecha: {fecha} — {hora}
            Jugadores: {jugadores}
            Árbitro: {arbitro_text}
            Total: ₡{precio_total}

            """
                text_content += """Importante: tienes 2 horas para realizar el adelanto y subir el comprobante.
Si no lo haces, tu reserva podría cancelarse automáticamente.
"""
                text_content += f"\nVer detalles de mi reserva: {reserva_url}\n\n"
                text_content += f"ID de reserva: {reserva_id}"

                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
                    to=[correo_reserva],
                    connection=tellos_connection
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                email_sent = True
                print(f"Reservation confirmation email sent successfully to: {correo_reserva}")
            else:
                print("No correo_reserva provided — skipping user confirmation email.")

            # Always notify admins, regardless of whether the client provided an email
            admin_email_sent = send_admin_notification(context, connection=tellos_connection)

        except Exception as e:
            print(f"Error sending email: {str(e)}")
        finally:
            tellos_connection.close()
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Reservation confirmed successfully',
            'email_sent': email_sent,
            'admin_email_sent': admin_email_sent,
            'reserva_id': reserva_id,
            'nombre_reserva': nombre_reserva
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error processing reservation: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
def send_test_email(request):
    """
    Send a test email using the Tellos email configuration.
    Expects a JSON body with 'email' field.
    """
    try:
        # Parse JSON data from request body
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
        
        # Validate email parameter
        if 'email' not in data:
            return JsonResponse({
                'error': 'Missing required field: email'
            }, status=400)
        
        recipient_email = data['email']
        
        # Create a connection using tellos email settings
        tellos_connection = get_tellos_connection()
        
        # Prepare email content
        subject = 'Hello from Tellos'
        message = 'Hello from Tellos! This is a test email.'
        from_email = settings.TELLOS_DEFAULT_FROM_EMAIL
        
        # Create and send email message using tellos connection
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=[recipient_email],
            connection=tellos_connection
        )
        
        # Send the email
        email.send()
        
        return JsonResponse({
            'success': True,
            'message': f'Test email sent successfully to {recipient_email}',
            'from_email': from_email
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error sending test email: {str(e)}")
        return JsonResponse({
            'error': 'Failed to send email',
            'details': str(e)
        }, status=500)


@api_view(['POST'])
def notify_new_reto(request):
    """
    Notify admin about a new reto (challenge) submitted.
    Sends an email to admin with reto details.
    """
    try:
        # Parse JSON data from request body
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
        
        # Define required fields
        required_fields = [
            'reto_id', 'hora_inicio', 'hora_fin', 'local', 'fut',
            'arbitro', 'cancha_id', 'cancha_nombre', 'equipo1_nombre',
            'equipo1_encargado', 'equipo1_celular', 'equipo1_correo',
            'precio_por_equipo'
        ]
        
        # Validate required fields
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        if missing_fields:
            return JsonResponse({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Extract data
        reto_id = data['reto_id']
        hora_inicio = data['hora_inicio']
        hora_fin = data['hora_fin']
        local = data['local']
        fut = data['fut']
        arbitro = data['arbitro']
        cancha_id = data['cancha_id']
        cancha_nombre = data['cancha_nombre']
        equipo1_nombre = data['equipo1_nombre']
        equipo1_encargado = data['equipo1_encargado']
        equipo1_celular = data['equipo1_celular']
        equipo1_correo = data['equipo1_correo']
        precio_por_equipo = data['precio_por_equipo']
        
        # Parse datetime strings
        try:
            inicio_dt = datetime.strptime(hora_inicio, '%Y-%m-%d %H:%M:%S')
            fin_dt = datetime.strptime(hora_fin, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return JsonResponse({
                'error': 'Invalid datetime format. Expected format: YYYY-MM-DD HH:MM:SS'
            }, status=400)
        
        # Format date and time for display (Spanish format)
        meses_espanol = {
            1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
            5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
            9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
        }
        fecha = f"{inicio_dt.day} de {meses_espanol[inicio_dt.month]} de {inicio_dt.year}"
        
        # Format time (convert to 12-hour format with Spanish AM/PM)
        hora_inicio_str = inicio_dt.strftime('%I:%M').lstrip('0')
        hora_fin_str = fin_dt.strftime('%I:%M').lstrip('0')
        periodo_inicio = 'AM' if inicio_dt.hour < 12 else 'PM'
        periodo_fin = 'AM' if fin_dt.hour < 12 else 'PM'
        hora = f"{hora_inicio_str} {periodo_inicio} - {hora_fin_str} {periodo_fin}"
        
        # Format arbitro text
        arbitro_text = 'Sí' if arbitro else 'No'
        
        # Format price with colones symbol
        precio_formatted = f"{precio_por_equipo:,}".replace(',', '.')
        
        # Prepare template context
        context = {
            'reto_id': reto_id,
            'equipo1_nombre': equipo1_nombre,
            'equipo1_encargado': equipo1_encargado,
            'equipo1_celular': equipo1_celular,
            'equipo1_correo': equipo1_correo,
            'cancha_nombre': cancha_nombre,
            'local': local,
            'fecha': fecha,
            'hora': hora,
            'fut': fut,
            'arbitro': arbitro_text,
            'precio_por_equipo': precio_formatted,
        }
        
        # Send admin notification email
        admin_email_sent = False
        
        try:
            tellos_connection = get_tellos_connection()
            
            # Build subject
            subject = f"Nuevo Reto: {equipo1_nombre} busca rival - {cancha_nombre}, {hora}"
            
            # Render HTML email template
            html_content = render_to_string('email_templates/tellos/admin_reto_notification.html', context)
            
            # Create plain text fallback
            text_content = f"""Nuevo Reto Registrado

            Equipo Retador: {equipo1_nombre}
            Encargado: {equipo1_encargado}
            Teléfono: {equipo1_celular}
            Correo: {equipo1_correo}

            Cancha: {cancha_nombre}
            Local: {local}
            Fecha: {fecha} — {hora}
            Modalidad: Fútbol {fut}
            Árbitro: {arbitro_text}
            Precio por Equipo: ₡{precio_formatted}

            Estado: Buscando rival

            ID de reto: {reto_id}
            """
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
                to=ADMIN_EMAILS,
                connection=tellos_connection
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            admin_email_sent = True
            print(f"Reto notification email sent successfully to: {ADMIN_EMAILS}")
            
        except Exception as e:
            print(f"Error sending reto notification email: {str(e)}")
            admin_email_sent = False
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Reto notification sent successfully',
            'admin_email_sent': admin_email_sent,
            'reto_id': reto_id,
            'equipo1_nombre': equipo1_nombre
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error processing reto notification: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

