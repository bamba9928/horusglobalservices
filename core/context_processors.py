from django.conf import settings


def global_settings(request):
    return {
        'WHATSAPP_URL': settings.WHATSAPP_URL,
        'GITHUB_URL': settings.GITHUB_URL,
        'LINKEDIN_URL': settings.LINKEDIN_URL,
        'FACEBOOK_URL': settings.FACEBOOK_URL,
        'X_URL': settings.X_URL,
        'PUBLIC_EMAIL': settings.PUBLIC_EMAIL,
        'GA_MEASUREMENT_ID': getattr(settings, 'GA_MEASUREMENT_ID', ''),
    }


def global_context(request):
    return {'TEMPLATE_DEBUG': settings.DEBUG}