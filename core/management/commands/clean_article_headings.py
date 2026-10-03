import json
import pathlib

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.article_cleanup import clean_article_html
from core.models import Article


class Command(BaseCommand):
    help = (
        "Nettoie les titres <h1> des articles (voir core/article_cleanup.py). "
        "Simulation par defaut : n'ecrit rien sans --apply, qui exige --backup."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="ecrit les modifications en base")
        parser.add_argument("--backup", help="fichier JSON recevant le contenu ORIGINAL de tous les articles (obligatoire avec --apply)")
        parser.add_argument("--only", type=int, nargs="*", help="limiter a ces identifiants d'articles")

    def handle(self, *args, **options):
        if options["apply"] and not options["backup"]:
            raise CommandError("--apply exige --backup <fichier.json> : sauvegarde obligatoire avant toute ecriture.")

        articles = Article.objects.order_by("id")
        if options["only"]:
            articles = articles.filter(pk__in=options["only"])

        plan = []
        for article in articles:
            new_content, changes = clean_article_html(article.content, article.title)
            plan.append((article, new_content, changes))
            label = ", ".join(f"{n} × {what}" for what, n in changes.items()) or "aucun changement"
            self.stdout.write(f"[{article.pk}] {article.title[:60]} — {label} ({len(article.content)} → {len(new_content)} octets)")

        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Simulation : rien n'a ete ecrit (relancer avec --apply --backup FICHIER)."))
            return

        backup = pathlib.Path(options["backup"])
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_text(
            json.dumps(
                [{"id": a.pk, "slug": a.slug, "title": a.title, "content": a.content} for a, _, _ in plan],
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        self.stdout.write(f"Sauvegarde ecrite : {backup} ({len(plan)} articles)")

        updated = 0
        for article, new_content, changes in plan:
            if changes:
                article.content = new_content
                article.updated_at = timezone.now()
                article.save(update_fields=["content", "updated_at"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"{updated} article(s) modifie(s)."))
