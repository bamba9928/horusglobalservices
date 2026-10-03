"""URLconf de test : ajoute une vue qui plante, pour verifier la page 500 et sa CSP."""
from django.urls import path

from config.urls import urlpatterns as project_urlpatterns


def boom(request):
    raise RuntimeError("erreur volontaire (test de la page 500)")


urlpatterns = [path("boom/", boom), *project_urlpatterns]
