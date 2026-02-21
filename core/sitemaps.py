from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Article, Project


class StaticViewSitemap(Sitemap):
    """Sitemap pour les pages institutionnelles fixes"""
    priority = 0.9  # Augmenté pour les pages piliers
    changefreq = 'monthly'

    def items(self):
        return ['home', 'services', 'skills', 'portfolio', 'blog', 'contact']

    def location(self, item):
        return reverse(item)


class ProjectSitemap(Sitemap):
    """Sitemap pour tes études de cas (Portfolio)"""
    changefreq = 'weekly'
    priority = 0.8 # Priorité haute pour tes réalisations

    def items(self):
        # On s'assure de l'ordre pour un sitemap stable
        return Project.objects.all().order_by('-id')

    def lastmod(self, obj):
        # Utilise updated_at si tu l'as, sinon created_at
        return getattr(obj, 'updated_at', obj.created_at)


class ArticleSitemap(Sitemap):
    """Sitemap pour les articles de blog"""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Article.objects.filter(is_published=True).order_by('-created_at')

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', obj.created_at)