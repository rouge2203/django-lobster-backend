from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.decorators import api_view
import json

def greetings(request):
    return HttpResponse("Hola Mariana")


@api_view(['GET'])
def greetings_email(request):
    message = request.GET.get('message')
    email = request.GET.get('email')
    if not message or not email:
        return HttpResponse("Error: Missing required parameters - message and email", status=400)
    #Send email
    send_mail('Hello from API', message, 'info@fcprosoccertryouts.com', [email])
    #Return response
    return HttpResponse("Email sent")

