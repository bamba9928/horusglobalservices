from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic.base import TemplateView, RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.admin.views.decorators import staff_member_required

from core.sitemaps import StaticViewSitemap, ArticleSitemap, ProjectSitemap

# Dictionnaire des sitemaps
sitemaps = {
    "static": StaticViewSitemap,
    "blog": ArticleSitemap,
    "projects": ProjectSitemap,
}

urlpatterns = [
    path("admin-horus/", admin.site.urls),
    path("", include("core.urls")),

    # CKEditor uploader protégé (admin interne / staff uniquement)
    path("ckeditor/", staff_member_required(include("ckeditor_uploader.urls"))),

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
    path(
        "favicon.ico",
        RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"), permanent=True),
    ),
]
handler404 = 'core.views.custom_bad_request_view'
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
