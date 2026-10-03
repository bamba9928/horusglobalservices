from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic.base import TemplateView, RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage

from core.sitemaps import StaticViewSitemap, ArticleSitemap, ProjectSitemap

# Dictionnaire des sitemaps
sitemaps = {
    "static": StaticViewSitemap,
    "blog": ArticleSitemap,
    "projects": ProjectSitemap,
}

class FaviconRedirectView(RedirectView):
    """/favicon.ico -> fichier statique, resolu A LA REQUETE.

    Avec le stockage a empreintes (production), staticfiles_storage.url() lit le manifeste de
    collectstatic : l'appeler a l'import de ce module faisait echouer tout `manage.py migrate`
    (qui charge les URL pour ses verifications) sur un serveur dont les statiques ne sont pas
    encore collectes ; deploy.sh lance migrate AVANT collectstatic.
    """

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        try:
            return staticfiles_storage.url("favicon.ico")
        except ValueError:  # statiques pas encore collectes
            return settings.STATIC_URL + "favicon.ico"


urlpatterns = [
    path("admin-horus/", admin.site.urls),
    path("", include("core.urls")),

    # CKEditor 5 : envoi d'images depuis l'éditeur (la vue refuse les non-staff : 403)
    path("ckeditor5/", include("django_ckeditor_5.urls")),

    # SEO : Sitemap.xml
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),

    # SEO : Robots.txt
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),

    # Les navigateurs demandent /favicon.ico a la racine, quels que soient les
    # <link rel="icon"> : sans cette redirection, chaque visite loggue un 404.
    path("favicon.ico", FaviconRedirectView.as_view()),
]
handler404 = 'core.views.custom_bad_request_view'
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
