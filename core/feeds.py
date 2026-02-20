from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Article

class LatestArticlesFeed(Feed):
    title = "Horus Global Services - Blog"
    link = "/blog/"
    description = "Derniers articles tech et tutoriels de Horuservices."

    def items(self):
        return Article.objects.filter(is_published=True).order_by('-created_at')[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.summary

    def item_pubdate(self, item):
        return item.created_at