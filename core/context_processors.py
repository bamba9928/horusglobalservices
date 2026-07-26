from functools import lru_cache
from pathlib import Path

from django.conf import settings


@lru_cache(maxsize=1)
def _css_version():
    """Empreinte de la CSS compilee, pour casser le cache a chaque build.

    L'URL /static/css/output.css est servie par Cloudflare avec
    "Cache-Control: max-age=2592000, immutable" : sans suffixe qui change,
    une modification de style met jusqu'a 30 jours a atteindre les visiteurs
    (c'est ce qui a masque la correction de la palette accent).

    On se base sur la date de modification du fichier : elle change a chaque
    "npm run build:css". Mis en cache pour ne pas toucher au disque a chaque
    requete ; le redemarrage de Gunicorn au deploiement vide ce cache.
    """
    for base in (Path(settings.STATIC_ROOT or ""), *map(Path, settings.STATICFILES_DIRS)):
        candidate = base / "css" / "output.css"
        try:
            return str(int(candidate.stat().st_mtime))
        except OSError:
            continue
    return ""


def global_settings(request):
    return {
        'CSS_VERSION': _css_version(),
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