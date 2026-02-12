from django.conf import settings

def global_settings(request):
    """
    Injecte les variables globales de settings.py dans tous les templates.
    """
    return {
        'WHATSAPP_URL': settings.WHATSAPP_URL,
        'PUBLIC_EMAIL': settings.PUBLIC_EMAIL,
    }