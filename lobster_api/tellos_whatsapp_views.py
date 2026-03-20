import json
import environ
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

env = environ.Env()
VERIFY_TOKEN = env('DUALHOOK_TOKEN')

@csrf_exempt
def whatsapp_webhook(request):
    # 1. Meta verification handshake (GET)
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge, status=200)
        return HttpResponse("Forbidden", status=403)

    # 2. Incoming messages / button taps (POST)
    if request.method == "POST":
        body = json.loads(request.body)
        
        # Extract the message
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        for msg in messages:
            phone = msg["from"]  # e.g. "50686167000"
            
            if msg["type"] == "button":
                # Customer tapped a quick reply button
                button_text = msg["button"]["text"]  # "Confirmar" or "Cancelar"
                
                # YOUR LOGIC HERE
                # look up reservation by phone number
                # handle confirm or cancel
                
            elif msg["type"] == "text":
                # Regular text message
                text = msg["text"]["body"]

        return JsonResponse({"status": "ok"}, status=200)