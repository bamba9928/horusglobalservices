"""Content-Security-Policy stricte, avec nonce par requete, pour le site public.

Pourquoi un middleware : la CSP posee par nginx est statique ('unsafe-inline' + 'unsafe-eval'
pour les scripts), donc sans protection reelle contre une injection de script. Ici chaque
reponse HTML recoit un nonce aleatoire ; seuls les <script>/<style> portant ce nonce
s'executent (voir csp_nonce dans core/context_processors.py et les templates).

- Site public : politique stricte (settings.CSP_DIRECTIVES).
- Admin / envoi d'images : aucune CSP posee ici (Unfold repose sur Alpine.js, qui exige
  'unsafe-eval') ; la CSP nginx continue de s'y appliquer.
- Page d'erreur 500 : politique minimale propre (page autonome avec <style> en ligne).
- Hors production (DEBUG) ou CSP_ENABLED=False : aucune politique.

Si une page HTML est un jour mise en cache (Cloudflare, cache Django), le nonce serait
reutilise entre visiteurs et la politique perdrait son interet : ne pas cacher le HTML.
"""
import secrets

from django.conf import settings

ENFORCE_HEADER = "Content-Security-Policy"
REPORT_ONLY_HEADER = "Content-Security-Policy-Report-Only"


def build_policy(directives, nonce=""):
    """{"script-src": ["'self'", "'nonce-{nonce}'"]} -> "script-src 'self' 'nonce-abc'; ..." """
    return "; ".join(
        f"{name} {' '.join(sources)}".format(nonce=nonce) for name, sources in directives.items()
    )


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        active = (
            settings.CSP_ENABLED
            and not settings.DEBUG
            and not request.path.startswith(tuple(settings.CSP_EXCLUDED_PATH_PREFIXES))
        )
        request.csp_nonce = secrets.token_urlsafe(16) if active else ""

        response = self.get_response(request)

        if active and response.get("Content-Type", "").startswith("text/html"):
            header = REPORT_ONLY_HEADER if settings.CSP_REPORT_ONLY else ENFORCE_HEADER
            if header not in response:  # une vue peut poser sa propre politique
                if response.status_code >= 500:
                    response[header] = build_policy(settings.CSP_SERVER_ERROR_DIRECTIVES)
                else:
                    response[header] = build_policy(settings.CSP_DIRECTIVES, request.csp_nonce)
        return response
