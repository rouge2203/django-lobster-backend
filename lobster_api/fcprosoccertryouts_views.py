from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.decorators import api_view
import json

@api_view(['POST'])
def submit_application(request):
    try:
        # Parse JSON data from request body
        if hasattr(request, 'data'):
            data = request.data
        else:
            data = json.loads(request.body.decode('utf-8'))
        
        # Define required fields
        required_fields = ['name', 'country', 'email', 'age', 'team', 'program']
        optional_fields = ['highlights', 'phone']
        
        # Validate required fields
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            return JsonResponse({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Extract data
        name = data['name']
        country = data['country']
        email = data['email']
        age = data['age']
        team = data['team']
        program = data['program']
        highlights = data.get('highlights', 'Not provided') if data.get('highlights') else 'Not provided'
        phone = data.get('phone', 'Not provided') if data.get('phone') else 'Not provided'
        
        # Send admin notification email
        admin_emails = [
            'aruiz@lobsterlabs.net',
            'jrodriguez@futbolconsultants.com',
            'info@fcprosoccertryouts.com',
            'arosales@futbolconsultants.com'
        ]
        
        admin_email_sent = False
        try:
            from datetime import datetime
            
            # Get current timestamp
            current_time = datetime.now()
            timestamp = current_time.strftime('%B %d, %Y at %I:%M %p')
            
            # Render HTML admin notification template
            admin_html_content = render_to_string('email_templates/fcprosoccertryouts/admin_notification.html', {
                'name': name,
                'email': email,
                'phone': phone,
                'age': age,
                'country': country,
                'team': team,
                'program': program,
                'highlights': highlights,
                'timestamp': timestamp
            })
            
            # Create plain text fallback for admins
            admin_text_content = f"""NEW APPLICATION RECEIVED
            
            Name: {name}
            Email: {email}
            Phone: {phone if phone else 'Not provided'}
            Age: {age}
            Country: {country}
            Team: {team}
            Program: {program}
            Highlights: {highlights if highlights else 'Not provided'}

            Received on: {timestamp}

            Please review and contact the applicant as soon as possible.
            """
            
            # Create admin email message
            admin_msg = EmailMultiAlternatives(
                subject=f"🚨 New Application: {name} - {program}",
                body=admin_text_content,
                from_email='info@fcprosoccertryouts.com',
                to=admin_emails
            )
            
            # Attach HTML content for admins
            admin_msg.attach_alternative(admin_html_content, "text/html")
            
            # Send admin email
            admin_msg.send()
            admin_email_sent = True
            print(f"Admin notification sent successfully to: {', '.join(admin_emails)}")
        except Exception as e:
            print(f"Error sending admin notification: {str(e)}")
            admin_email_sent = False
        
        # Send confirmation email with HTML template
        subject = "Application Received - We'll Contact You Soon"
        
        try:
            # Render HTML email template
            html_content = render_to_string('email_templates/fcprosoccertryouts/application_confirmation.html', {
                'name': name
            })
            
            # Create plain text fallback
            text_content = f"Hello {name},\n\nWe received your application and we'll contact you soon.\n\nThank you for your interest!\n\nBest regards,\nFC Pro Soccer Tryouts"
            
            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email='info@fcprosoccertryouts.com',
                to=[email]
            )
            
            # Attach HTML content
            msg.attach_alternative(html_content, "text/html")
            
            # Send email
            msg.send()
            email_sent = True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            email_sent = False
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': 'Application received successfully',
            'applicant_email_sent': email_sent,
            'admin_email_sent': admin_email_sent,
            'applicant_name': name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Error processing application: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

