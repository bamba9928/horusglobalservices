from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('competences/', views.skills, name='skills'),
    path('contact/', views.contact, name='contact'),
]