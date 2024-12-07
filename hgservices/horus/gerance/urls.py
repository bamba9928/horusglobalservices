# ....Mouhamadou Bamba Dieng ... 2024  Horus Global Services ...
#..... +221 77 249 05 30 bigrip2016@gmail.com ....

from django.contrib.auth import views as auth_views
from django.urls import path
from . import views
from .views import export_vehicles_csv
from .views import (
    VehiculeCreateView,
    VehiculeUpdateView,
    VehiculeDeleteView,
    VehiculeListView,
)



handler404 = 'gerance.views.custom_page_not_found_view'


urlpatterns = [
    # Page d'accueil
    path('', views.home, name='home'),

    # Authentification
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Gestion générale
    path('gestion/', views.gestion, name='gestion'),

    # Gestion des véhicules
    path('vehicules/', VehiculeListView.as_view(), name='vehicule_list'),
    path('vehicule/ajouter/', VehiculeCreateView.as_view(), name='vehicule_create'),
    path('vehicule/modifier/<int:pk>/', VehiculeUpdateView.as_view(), name='vehicule_update'),
    path('vehicule/supprimer/<int:pk>/', VehiculeDeleteView.as_view(), name='vehicule_delete'),
    # Fonctionnalité de recherche
    path('search/', views.search, name='search'),
    path('export/csv/', export_vehicles_csv, name='export_vehicles_csv'),
    path('export/vehicules/csv/', views.export_vehicules_csv, name='export_vehicules_csv'),
    path('export/vehicules/pdf/', views.export_vehicules_pdf, name='export_vehicules_pdf'),
]
