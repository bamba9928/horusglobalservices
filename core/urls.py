from django.urls import path
from . import views
from .feeds import LatestArticlesFeed

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('competences/', views.skills, name='skills'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.article_detail, name='article_detail'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio/<slug:slug>/', views.project_detail, name='project_detail'),
    path('contact/', views.contact, name='contact'),
    path('feed.xml', LatestArticlesFeed(), name='article_feed'),
    path('legal/<slug:slug>/', views.legal_page_detail, name='legal_page'),
]
