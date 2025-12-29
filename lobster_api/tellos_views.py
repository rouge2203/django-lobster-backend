from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.decorators import api_view
from datetime import datetime
import json

@api_view(['POST'])
def confirm_reservation(request):
    try:
        # Parse JSON data from request body
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
        
        # Define required fields
        required_fields = [
            'reserva_id', 'hora_inicio', 'hora_fin', 'cancha_id', 
            'cancha_nombre', 'cancha_local', 'nombre_reserva', 
            'celular_reserva', 'correo_reserva', 'precio', 
            'arbitro', 'jugadores', 'reserva_url'
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
        reserva_id = data['reserva_id']
        hora_inicio = data['hora_inicio']
        hora_fin = data['hora_fin']
        cancha_id = data['cancha_id']
        cancha_nombre = data['cancha_nombre']
        cancha_local = data['cancha_local']
        nombre_reserva = data['nombre_reserva']
        celular_reserva = data['celular_reserva']
        correo_reserva = data['correo_reserva']
        precio = data['precio']
        arbitro = data['arbitro']
        jugadores = data['jugadores']
        reserva_url = data['reserva_url']
        
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
        local_nombre = 'Sabana' if cancha_local == 1 else 'Guadalupe'
        
        # Format arbitro text
        arbitro_text = 'Sí' if arbitro else 'No'
        
        # Format price with colones symbol
        precio_total = f"{precio:,}".replace(',', '.')
        
        # Prepare template context
        context = {
            'nombre_reserva': nombre_reserva,
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
        }
        
        subject = f"Futbol Tello: Reservación confirmada"
        
        # Send confirmation email
        email_sent = False
        try:
            # Render HTML email template
            html_content = render_to_string('email_templates/tellos/reservation_confirmation.html', context)
            
            # Create plain text fallback
            text_content = f"""¡Reserva confirmada!

Hola {nombre_reserva}, tu reserva ya está registrada.

Cancha: {cancha_nombre}
Local: {local_nombre}
Fecha: {fecha} — {hora}
Jugadores: {jugadores}
Árbitro: {arbitro_text}
Total: ₡{precio_total}

"""
            
            if cancha_local == 1:
                text_content += """Importante: tienes 2 horas para realizar el SINPE y subir el comprobante.
Si no lo haces, tu reserva podría cancelarse automáticamente.
"""
            else:
                text_content += "Pago: se realiza directamente en la cancha.\n"
            
            text_content += f"\nVer detalles de mi reserva: {reserva_url}\n\n"
            text_content += f"ID de reserva: {reserva_id}"
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email='info@fcprosoccertryouts.com',
                to=[correo_reserva]
            )
            
            # Attach HTML content
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            email_sent = True
            print(f"Reservation confirmation email sent successfully to: {correo_reserva}")
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            email_sent = False
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Reservation confirmed successfully',
            'email_sent': email_sent,
            'reserva_id': reserva_id,
            'nombre_reserva': nombre_reserva
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error processing reservation: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

