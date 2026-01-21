"""
Cron tasks for Futbol Tello.
These endpoints are called by Vercel cron jobs.
"""
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from rest_framework.decorators import api_view
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from io import BytesIO
from .supabase_client import get_supabase_client

# PDF generation imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Costa Rica timezone (UTC-6, no daylight saving)
COSTA_RICA_TZ = ZoneInfo('America/Costa_Rica')

# Admin email for cron summaries
ADMIN_EMAIL = 'aruiz@lobsterlabs.net'

# Spanish day names
DIAS_ESPANOL = {
    0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves',
    4: 'Viernes', 5: 'Sábado', 6: 'Domingo'
}

# Spanish month names
MESES_ESPANOL = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre'
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
    
    # Get sinpe_reserva for SINPE payment check (Sabana only)
    sinpe_reserva = reserva.get('sinpe_reserva', None)
    
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
        'sinpe_reserva': sinpe_reserva,
    }


def send_reminder_email(context, connection):
    """
    Send 24h reminder email to customer.
    Returns (success: bool, error_message: str or None)
    """
    try:
        subject = f"Recordatorio: Su reserva es mañana - {context['cancha_nombre']}"
        
        # Render HTML email template
        html_content = render_to_string('email_templates/tellos/reminder_24h.html', context)
        
        # Create plain text fallback
        text_content = f"""Recordatorio de Reservación

Hola {context['nombre_reserva']}, le recordamos que tiene una reservación programada para mañana.

Cancha: {context['cancha_nombre']}
Local: {context['local_nombre']}
Fecha: {context['fecha']} — {context['hora']}
Jugadores: {context['jugadores']}
Árbitro: {context['arbitro']}
Total: ₡{context['precio_total']}
"""
        
        # Add SINPE warning for Sabana if payment not received
        if context['local_id'] == 1 and not context.get('sinpe_reserva'):
            text_content += """
⚠️ IMPORTANTE - Pago Pendiente
No hemos recibido su comprobante de SINPE. Si no realiza el pago y sube el comprobante, su reservación podría ser cancelada.
"""
        
        text_content += f"""
Ver detalles de su reserva: {context['reserva_url']}

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
        
        # Calculate time window: from NOW to 24 hours from now
        # hora_inicio is stored in Costa Rica time (UTC-6), so we use that timezone
        now_utc = datetime.now(timezone.utc)
        now_cr = now_utc.astimezone(COSTA_RICA_TZ)
        
        # Window: from now until 24 hours from now (Costa Rica time)
        window_start = now_cr
        window_end = now_cr + timedelta(hours=24)
        
        # Format for Supabase query (without timezone info, matching hora_inicio format)
        window_start_str = window_start.strftime('%Y-%m-%d %H:%M:%S')
        window_end_str = window_end.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Current time (Costa Rica): {now_cr.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Checking for reservations between {window_start_str} and {window_end_str}")
        
        # Query reservations that need reminders
        # - recordatorio_24h_enviado is NULL (no reminder sent yet)
        # - correo_reserva is NOT NULL (has email to send to)
        # - hora_inicio is between now and 24 hours from now
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
                    
                    # Update recordatorio_24h_enviado with current timestamp (Costa Rica time)
                    timestamp_cr = datetime.now(timezone.utc).astimezone(COSTA_RICA_TZ)
                    timestamp_str = timestamp_cr.strftime('%Y-%m-%d %H:%M:%S')
                    supabase.table('reservas').update({
                        'recordatorio_24h_enviado': timestamp_str
                    }).eq('id', reserva['id']).execute()
                    print(f"Updated recordatorio_24h_enviado for reserva {reserva['id']} at {timestamp_str}")
                    
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


def generate_daily_schedule_pdf(date_cr, canchas, reservations_by_cancha):
    """
    Generate a PDF with the daily schedule for all canchas.
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = BytesIO()
    
    # Create document in landscape mode for better calendar view
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.75*inch
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1d'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#666666'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    cancha_title_style = ParagraphStyle(
        'CanchaTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a1d'),
        spaceBefore=20,
        spaceAfter=10,
        alignment=TA_LEFT
    )
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    no_reservations_style = ParagraphStyle(
        'NoReservations',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#999999'),
        alignment=TA_LEFT,
        leftIndent=20
    )
    
    # Build content
    elements = []
    
    # Title
    dia_semana = DIAS_ESPANOL[date_cr.weekday()]
    fecha_formateada = f"{dia_semana}, {date_cr.day} de {MESES_ESPANOL[date_cr.month]} de {date_cr.year}"
    elements.append(Paragraph("FUTBOL TELLO", title_style))
    elements.append(Paragraph(f"Agenda del Día: {fecha_formateada}", subtitle_style))
    
    # Group canchas by local
    canchas_sabana = [c for c in canchas if c['local'] == 1]
    canchas_guadalupe = [c for c in canchas if c['local'] == 2]
    
    def add_cancha_section(cancha, reservations):
        """Add a section for a single cancha with its reservations."""
        local_name = "Sabana" if cancha['local'] == 1 else "Guadalupe"
        elements.append(Paragraph(
            f"<b>{cancha['nombre']}</b> - {local_name} (Fútbol {cancha['cantidad']})",
            cancha_title_style
        ))
        
        if not reservations:
            elements.append(Paragraph("Sin reservaciones para hoy", no_reservations_style))
            elements.append(Spacer(1, 10))
            return
        
        # Sort reservations by hora_inicio
        reservations.sort(key=lambda x: x['hora_inicio'])
        
        # Create table data
        table_data = [['Hora', 'Cliente', 'Teléfono', 'Árbitro', 'Precio', 'Confirmada']]
        
        for res in reservations:
            # Parse time
            try:
                inicio_dt = datetime.strptime(res['hora_inicio'], '%Y-%m-%d %H:%M:%S')
                fin_dt = datetime.strptime(res['hora_fin'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                inicio_dt = datetime.fromisoformat(res['hora_inicio'].replace('Z', '+00:00'))
                fin_dt = datetime.fromisoformat(res['hora_fin'].replace('Z', '+00:00'))
            
            hora_inicio_str = inicio_dt.strftime('%I:%M %p').lstrip('0')
            hora_fin_str = fin_dt.strftime('%I:%M %p').lstrip('0')
            hora = f"{hora_inicio_str} - {hora_fin_str}"
            
            # Format data
            nombre = res.get('nombre_reserva', 'N/A')
            celular = res.get('celular_reserva', 'N/A') or 'N/A'
            arbitro = 'Sí' if res.get('arbitro', False) else 'No'
            precio = f"₡{res.get('precio', 0):,}".replace(',', '.')
            confirmada = 'Sí' if res.get('confirmada', False) else 'No'
            
            table_data.append([hora, nombre, celular, arbitro, precio, confirmada])
        
        # Create table
        col_widths = [1.5*inch, 2.5*inch, 1.3*inch, 0.8*inch, 1*inch, 1*inch]
        table = Table(table_data, colWidths=col_widths)
        
        # Table styling
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 1), (5, -1), 'CENTER'),  # Center arbitro, precio, confirmada
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1a1a1d')),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 15))
    
    # Add Sabana section
    if canchas_sabana:
        elements.append(Paragraph("<b>📍 LOCAL: SABANA</b>", ParagraphStyle(
            'LocalTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1d'),
            spaceBefore=10,
            spaceAfter=5,
            alignment=TA_LEFT
        )))
        elements.append(Spacer(1, 5))
        
        for cancha in sorted(canchas_sabana, key=lambda x: x['nombre']):
            reservations = reservations_by_cancha.get(cancha['id'], [])
            add_cancha_section(cancha, reservations)
    
    # Add Guadalupe section
    if canchas_guadalupe:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("<b>📍 LOCAL: GUADALUPE</b>", ParagraphStyle(
            'LocalTitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1d'),
            spaceBefore=10,
            spaceAfter=5,
            alignment=TA_LEFT
        )))
        elements.append(Spacer(1, 5))
        
        for cancha in sorted(canchas_guadalupe, key=lambda x: x['nombre']):
            reservations = reservations_by_cancha.get(cancha['id'], [])
            add_cancha_section(cancha, reservations)
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("─" * 80, footer_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Powered by LOBSTER LABS", ParagraphStyle(
        'PoweredBy',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )))
    elements.append(Paragraph("www.lobsterlabs.net", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


@api_view(['GET'])
def send_daily_schedule(request):
    """
    Cron task: Generate daily schedule PDF and send to admin.
    Called by Vercel cron every day at 6 AM Costa Rica time.
    """
    # Verify cron secret
    auth_header = request.headers.get('Authorization', '')
    expected_secret = f"Bearer {settings.CRON_SECRET}"
    
    if settings.CRON_SECRET and auth_header != expected_secret:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Get current date in Costa Rica
        now_utc = datetime.now(timezone.utc)
        now_cr = now_utc.astimezone(COSTA_RICA_TZ)
        today_cr = now_cr.date()
        
        # Format date strings for query
        day_start = f"{today_cr.strftime('%Y-%m-%d')} 00:00:00"
        day_end = f"{today_cr.strftime('%Y-%m-%d')} 23:59:59"
        
        print(f"Generating daily schedule for {today_cr}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Fetch all canchas
        canchas_response = supabase.table('canchas').select('*').execute()
        canchas = canchas_response.data
        print(f"Found {len(canchas)} canchas")
        
        # Fetch all reservations for today
        reservations_response = supabase.table('reservas').select('*').gte('hora_inicio', day_start).lte('hora_inicio', day_end).execute()
        reservations = reservations_response.data
        print(f"Found {len(reservations)} reservations for today")
        
        # Group reservations by cancha_id
        reservations_by_cancha = {}
        for res in reservations:
            cancha_id = res['cancha_id']
            if cancha_id not in reservations_by_cancha:
                reservations_by_cancha[cancha_id] = []
            reservations_by_cancha[cancha_id].append(res)
        
        # Generate PDF
        pdf_buffer = generate_daily_schedule_pdf(now_cr, canchas, reservations_by_cancha)
        
        # Prepare email
        dia_semana = DIAS_ESPANOL[now_cr.weekday()]
        fecha_formateada = f"{dia_semana}, {now_cr.day} de {MESES_ESPANOL[now_cr.month]} de {now_cr.year}"
        
        subject = f"📅 Agenda del Día - {fecha_formateada}"
        
        text_content = f"""¡Buenos días!

Aquí está la agenda de reservaciones para el día de hoy.

Fecha: {fecha_formateada}
Total de reservaciones: {len(reservations)}

Se adjunta el PDF con el detalle completo de las reservaciones por cancha.

---
Powered by LOBSTER LABS
www.lobsterlabs.net
"""
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; margin: 0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <tr>
            <td style="background: #1a1a1d; padding: 24px; text-align: center;">
                <h1 style="margin: 0; color: white; font-size: 20px; font-weight: 800;">FUTBOL TELLO</h1>
            </td>
        </tr>
        <tr>
            <td style="padding: 32px 24px;">
                <h2 style="margin: 0 0 16px 0; color: #1a1a1d; font-size: 24px;">¡Buenos días! ☀️</h2>
                <p style="margin: 0 0 24px 0; color: #666; font-size: 16px; line-height: 1.6;">
                    Aquí está la agenda de reservaciones para el día de hoy.
                </p>
                
                <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                    <p style="margin: 0 0 8px 0; color: #999; font-size: 12px; text-transform: uppercase;">Fecha</p>
                    <p style="margin: 0 0 16px 0; color: #1a1a1d; font-size: 18px; font-weight: 600;">{fecha_formateada}</p>
                    
                    <p style="margin: 0 0 8px 0; color: #999; font-size: 12px; text-transform: uppercase;">Total de Reservaciones</p>
                    <p style="margin: 0; color: #1a1a1d; font-size: 32px; font-weight: 700;">{len(reservations)}</p>
                </div>
                
                <p style="margin: 0 0 16px 0; color: #666; font-size: 14px;">
                    📎 Se adjunta el PDF con el detalle completo de las reservaciones por cancha.
                </p>
            </td>
        </tr>
        <tr>
            <td style="background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                <p style="margin: 0 0 4px 0; color: #666; font-size: 12px; font-weight: 600;">Powered by LOBSTER LABS</p>
                <p style="margin: 0; color: #999; font-size: 11px;">www.lobsterlabs.net</p>
            </td>
        </tr>
    </table>
</body>
</html>
"""
        
        # Send email with PDF attachment
        tellos_connection = get_tellos_connection()
        
        try:
            tellos_connection.open()
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.TELLOS_DEFAULT_FROM_EMAIL,
                to=[ADMIN_EMAIL],
                connection=tellos_connection
            )
            
            msg.attach_alternative(html_content, "text/html")
            
            # Attach PDF
            pdf_filename = f"agenda_{today_cr.strftime('%Y-%m-%d')}.pdf"
            msg.attach(pdf_filename, pdf_buffer.getvalue(), 'application/pdf')
            
            msg.send()
            print(f"Daily schedule email sent to {ADMIN_EMAIL}")
            
        finally:
            tellos_connection.close()
        
        return JsonResponse({
            'success': True,
            'message': f'Daily schedule sent for {today_cr}',
            'reservations_count': len(reservations),
            'canchas_count': len(canchas)
        })
        
    except Exception as e:
        print(f"Error in send_daily_schedule: {str(e)}")
        return JsonResponse({
            'error': 'Internal server error',
            'details': str(e)
        }, status=500)
