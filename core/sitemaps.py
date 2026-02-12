from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Article, Project


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'services', 'skills', 'portfolio', 'blog', 'contact']

    def location(self, item):
        return reverse(item)


class ArticleSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Article.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.created_at


class ProjectSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Project.objects.all()

    def lastmod(self, obj):
        return obj.created_at
