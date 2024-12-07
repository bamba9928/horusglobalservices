"""
URL configuration for hgservices project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# ....Mouhamadou Bamba Dieng ... 2024  Horus Global Services ...
#..... +221 77 249 05 30    bigrip2016@gmail.com ....


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),            # Route pour l'administration
    path('gerance/', include('gerance.urls')),  # Inclut les URLs de mon application
    path('', include('gerance.urls')),
    path('accounts/', include('allauth.urls')),
]

# Ajouter les configurations pour servir les fichiers statiques et médias
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS)


