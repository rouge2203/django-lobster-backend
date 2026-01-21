"""
Cron tasks for Futbol Tello.
These endpoints are called by Vercel cron jobs.
"""
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.decorators import api_view
from datetime import datetime, timedelta
from .supabase_client import get_supabase_client

# Admin email for cron summaries
ADMIN_EMAIL = 'aruiz@lobsterlabs.net'


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


def format_reservation_for_email(reserva, cancha):
    """
    Format reservation and cancha data for email template context.
    """
    # Parse datetime strings
    hora_inicio = reserva['hora_inicio']
    hora_fin = reserva['hora_fin']
    
    try:
        inicio_dt = datetime.strptime(hora_inicio, '%Y-%m-%d %H:%M:%S')
        fin_dt = datetime.strptime(hora_fin, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Try alternative format
        inicio_dt = datetime.fromisoformat(hora_inicio.replace('Z', '+00:00'))
        fin_dt = datetime.fromisoformat(hora_fin.replace('Z', '+00:00'))
    
    # Spanish month names
    meses_espanol = {
        1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
        5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
        9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
    }
    fecha = f"{inicio_dt.day} de {meses_espanol[inicio_dt.month]} de {inicio_dt.year}"
    
    # Format time (12-hour format)
    hora_inicio_str = inicio_dt.strftime('%I:%M').lstrip('0')
    hora_fin_str = fin_dt.strftime('%I:%M').lstrip('0')
    periodo_inicio = 'AM' if inicio_dt.hour < 12 else 'PM'
    periodo_fin = 'AM' if fin_dt.hour < 12 else 'PM'
    hora = f"{hora_inicio_str} {periodo_inicio} - {hora_fin_str} {periodo_fin}"
    
    # Determine local name
    local_id = cancha['local']
    local_nombre = 'Sabana' if local_id == 1 else 'Guadalupe'
    
    # Format arbitro text
    arbitro_text = 'Sí' if reserva.get('arbitro', False) else 'No'
    
    # Format price
    precio = reserva.get('precio', 0)
    precio_total = f"{precio:,}".replace(',', '.')
    
    # Calculate jugadores from cancha cantidad
    cantidad = cancha.get('cantidad', '5')
    # Handle variable cantidad like "7-8-9"
    if '-' in str(cantidad):
        jugadores = f"Fútbol {cantidad}"
    else:
        jugadores = f"{cantidad} vs {cantidad}"
    
    # Build reserva URL
    reserva_url = f"https://futboltello.com/reserva/{reserva['id']}"
    
    return {
        'nombre_reserva': reserva['nombre_reserva'],
        'celular_reserva': reserva.get('celular_reserva', ''),
        'correo_reserva': reserva['correo_reserva'],
        'cancha_nombre': cancha['nombre'],
        'local_nombre': local_nombre,
        'local_id': local_id,
        'fecha': fecha,
        'hora': hora,
        'jugadores': jugadores,
        'arbitro': arbitro_text,
        'precio_total': precio_total,
        'reserva_id': reserva['id'],
        'reserva_url': reserva_url,
    }


def send_reminder_email(context, connection):
    """
    Send 24h reminder email to customer.
    Returns (success: bool, error_message: str or None)
    """
    try:
        subject = f"Recordatorio: Tu reserva es mañana - {context['cancha_nombre']}"
        
        # Render HTML email template
        html_content = render_to_string('email_templates/tellos/reminder_24h.html', context)
        
        # Create plain text fallback
        text_content = f"""Recordatorio de Reservación

Hola {context['nombre_reserva']}, te recordamos que tienes una reservación programada para mañana.

Cancha: {context['cancha_nombre']}
Local: {context['local_nombre']}
Fecha: {context['fecha']} — {context['hora']}
Jugadores: {context['jugadores']}
Árbitro: {context['arbitro']}
Total: ₡{context['precio_total']}

Ver detalles de mi reserva: {context['reserva_url']}

ID de reserva: {context['reserva_id']}
"""
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
            to=[context['correo_reserva']],
            connection=connection
        )
        
        # Attach HTML content
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        print(f"Reminder email sent to: {context['correo_reserva']} for reserva {context['reserva_id']}")
        return True, None
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error sending reminder email to {context['correo_reserva']}: {error_msg}")
        return False, error_msg


def send_summary_email(emails_sent, emails_failed, success_list, failure_list, connection):
    """
    Send summary email to admin with results of the cron job.
    """
    try:
        execution_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        context = {
            'execution_time': execution_time,
            'emails_sent': emails_sent,
            'emails_failed': emails_failed,
            'success_list': success_list,
            'failure_list': failure_list,
        }
        
        subject = f"[Cron] Recordatorios 24h: {emails_sent} enviados, {emails_failed} errores"
        
        # Render HTML email template
        html_content = render_to_string('email_templates/tellos/cron_summary.html', context)
        
        # Create plain text fallback
        text_content = f"""Resumen de Recordatorios 24h
Ejecutado: {execution_time}

Emails Enviados: {emails_sent}
Errores: {emails_failed}

"""
        if success_list:
            text_content += "ENVIADOS CORRECTAMENTE:\n"
            for item in success_list:
                text_content += f"- Reserva #{item['reserva_id']} - {item['nombre']} ({item['email']})\n"
            text_content += "\n"
        
        if failure_list:
            text_content += "ERRORES:\n"
            for item in failure_list:
                text_content += f"- Reserva #{item['reserva_id']} - {item['nombre']} ({item['email']}): {item['error']}\n"
        
        # Create email message
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
            to=[ADMIN_EMAIL],
            connection=connection
        )
        
        # Attach HTML content
        msg.attach_alternative(html_content, "text/html")
        
        # Send email
        msg.send()
        print(f"Summary email sent to: {ADMIN_EMAIL}")
        return True
        
    except Exception as e:
        print(f"Error sending summary email: {str(e)}")
        return False


@api_view(['GET'])
def send_24h_reminders(request):
    """
    Cron task: Find reservations 24h away, send reminder emails, update timestamp.
    Called by Vercel cron every 5 minutes.
    
    Security: Vercel cron jobs include an Authorization header that we can verify.
    """
    # Verify cron secret (Vercel sends this automatically for cron jobs)
    auth_header = request.headers.get('Authorization', '')
    expected_secret = f"Bearer {settings.CRON_SECRET}"
    
    # Allow if CRON_SECRET is empty (for development) or matches
    if settings.CRON_SECRET and auth_header != expected_secret:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Calculate time window for 24 hours from now
        # We use a 2-hour window (23h to 25h) to ensure we don't miss any
        # with the 5-minute cron interval
        now = datetime.now()
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)
        
        # Format for Supabase query
        window_start_str = window_start.strftime('%Y-%m-%d %H:%M:%S')
        window_end_str = window_end.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Checking for reservations between {window_start_str} and {window_end_str}")
        
        # Query reservations that need reminders
        # - recordatorio_24h_enviado is NULL
        # - correo_reserva is NOT NULL
        # - hora_inicio is between 23-25 hours from now
        response = supabase.table('reservas').select('*').is_('recordatorio_24h_enviado', 'null').not_.is_('correo_reserva', 'null').gte('hora_inicio', window_start_str).lte('hora_inicio', window_end_str).execute()
        
        reservations = response.data
        print(f"Found {len(reservations)} reservations needing reminders")
        
        if not reservations:
            return JsonResponse({
                'success': True,
                'message': 'No reservations need reminders at this time',
                'emails_sent': 0,
                'emails_failed': 0
            })
        
        # Get unique cancha IDs
        cancha_ids = list(set(r['cancha_id'] for r in reservations))
        
        # Fetch cancha details
        canchas_response = supabase.table('canchas').select('*').in_('id', cancha_ids).execute()
        canchas = {c['id']: c for c in canchas_response.data}
        
        # Track results
        emails_sent = 0
        emails_failed = 0
        success_list = []
        failure_list = []
        
        # Create email connection
        tellos_connection = get_tellos_connection()
        
        try:
            tellos_connection.open()
            
            for reserva in reservations:
                cancha_id = reserva['cancha_id']
                cancha = canchas.get(cancha_id)
                
                if not cancha:
                    print(f"Cancha {cancha_id} not found for reserva {reserva['id']}")
                    emails_failed += 1
                    failure_list.append({
                        'reserva_id': reserva['id'],
                        'nombre': reserva['nombre_reserva'],
                        'email': reserva['correo_reserva'],
                        'error': f'Cancha {cancha_id} not found'
                    })
                    continue
                
                # Format data for email
                context = format_reservation_for_email(reserva, cancha)
                
                # Send reminder email
                success, error = send_reminder_email(context, tellos_connection)
                
                if success:
                    emails_sent += 1
                    success_list.append({
                        'reserva_id': reserva['id'],
                        'nombre': reserva['nombre_reserva'],
                        'email': reserva['correo_reserva'],
                        'cancha': cancha['nombre'],
                        'fecha': context['fecha'],
                        'hora': context['hora']
                    })
                    
                    # Update recordatorio_24h_enviado with current timestamp
                    timestamp = datetime.now().isoformat()
                    supabase.table('reservas').update({
                        'recordatorio_24h_enviado': timestamp
                    }).eq('id', reserva['id']).execute()
                    print(f"Updated recordatorio_24h_enviado for reserva {reserva['id']}")
                    
                else:
                    emails_failed += 1
                    failure_list.append({
                        'reserva_id': reserva['id'],
                        'nombre': reserva['nombre_reserva'],
                        'email': reserva['correo_reserva'],
                        'error': error
                    })
            
            # Send summary email if any emails were attempted
            if emails_sent > 0 or emails_failed > 0:
                send_summary_email(emails_sent, emails_failed, success_list, failure_list, tellos_connection)
            
        finally:
            tellos_connection.close()
        
        return JsonResponse({
            'success': True,
            'message': f'Processed {len(reservations)} reservations',
            'emails_sent': emails_sent,
            'emails_failed': emails_failed
        })
        
    except Exception as e:
        print(f"Error in send_24h_reminders: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)
