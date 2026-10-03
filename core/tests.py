from pathlib import Path
from unittest.mock import patch

import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.views.defaults import server_error

from .forms import ContactForm
from .models import Article, Contact, Project
from .views import MARQUEE_MIN_CARDS

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"


def _template_files():
    return sorted(
        p for p in TEMPLATES_DIR.rglob("*") if p.suffix in {".html", ".txt"}
    )


class ContactFormTests(TestCase):
    def test_contact_form_strips_name_message_and_phone(self):
        form = ContactForm(
            data={
                "name": "  Alice Ndiaye  ",
                "email": "alice@example.com",
                "phone": "  +221 77 123 45 67  ",
                "message": "  Besoin d'un audit sécurité complet.  ",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "Alice Ndiaye")
        self.assertEqual(form.cleaned_data["phone"], "+221 77 123 45 67")
        self.assertEqual(
            form.cleaned_data["message"], "Besoin d'un audit sécurité complet."
        )

    def test_contact_form_rejects_invalid_phone(self):
        form = ContactForm(
            data={
                "name": "Alice Ndiaye",
                "email": "alice@example.com",
                "phone": "invalid-phone",
                "message": "Besoin d'un audit sécurité complet.",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)


class ContactViewTests(TestCase):
    @patch("core.views.send_mail")
    def test_contact_view_audit_type_is_preserved_on_post(self, send_mail_mock):
        response = self.client.post(
            reverse("contact"),
            data={
                "request_type": "audit",
                "name": "Alice Ndiaye",
                "email": "alice@example.com",
                "phone": "+221771234567",
                "message": "Bonjour, je souhaite un audit applicatif complet.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contact.objects.count(), 1)

        send_mail_mock.assert_called_once()
        args, _ = send_mail_mock.call_args
        self.assertIn("DEMANDE D'AUDIT", args[0])
        self.assertIn("Type : Audit", args[1])

    def test_contact_view_prefills_audit_message_on_get(self):
        response = self.client.get(reverse("contact"), {"type": "audit"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mode audit prioritaire activé")
        self.assertContains(response, "audit complet")

class TemplateSanityTests(SimpleTestCase):
    def test_no_multiline_django_comments(self):
        """{# ... #} doit tenir sur UNE ligne : Django n'interprete pas un
        commentaire multi-ligne, qui s'affiche alors en clair sur le site.
        Pour plusieurs lignes, utiliser {% comment %} ... {% endcomment %}."""
        offenders = []
        for path in _template_files():
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), start=1):
                start = line.find("{#")
                while start != -1:
                    end = line.find("#}", start + 2)
                    if end == -1:
                        offenders.append(f"{path.relative_to(TEMPLATES_DIR)}:{number}")
                        break
                    start = line.find("{#", end + 2)

        self.assertEqual(
            offenders,
            [],
            "Commentaire {# #} multi-ligne (affiche en clair) : utiliser "
            "{% comment %}...{% endcomment %}",
        )

    def test_all_templates_compile(self):
        for path in _template_files():
            get_template(path.relative_to(TEMPLATES_DIR).as_posix())


class HomeCarouselTests(TestCase):
    def _create_projects(self, count):
        for i in range(count):
            Project.objects.create(
                title=f"Projet {i}",
                slug=f"projet-{i}",
                description="Description du projet. " * 5,
                image=f"portfolio/projet-{i}.webp",
                technologies="Django, Tailwind",
                is_featured=True,
            )

    def test_home_renders_carousel_without_leaking_template_syntax(self):
        self._create_projects(2)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="project-marquee__track"')
        self.assertNotContains(response, "{#")
        self.assertNotContains(response, "{%")

    def test_only_first_copy_is_exposed_to_screen_readers(self):
        self._create_projects(2)

        html = self.client.get(reverse("home")).content.decode()

        self.assertEqual(html.count('aria-label="Voir le projet'), 2)

    def test_carousel_repeats_projects_to_fill_the_loop(self):
        self._create_projects(1)

        html = self.client.get(reverse("home")).content.decode()

        # 2 moities identiques, chacune d'au moins MARQUEE_MIN_CARDS cartes
        self.assertEqual(
            html.count('class="project-marquee__item'), 2 * MARQUEE_MIN_CARDS
        )

    def test_home_without_featured_projects_has_no_carousel(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="project-marquee__track"')


def _make_article(slug="mon-article", published=True, **extra):
    return Article.objects.create(
        title=extra.pop("title", f"Article {slug}"),
        slug=slug,
        summary=extra.pop("summary", "Résumé de l'article."),
        content=extra.pop("content", "<p>Contenu de l'article.</p>"),
        is_published=published,
        **extra,
    )


def _make_project(slug="mon-projet", **extra):
    return Project.objects.create(
        title=extra.pop("title", f"Projet {slug}"),
        slug=slug,
        description=extra.pop("description", "Description du projet."),
        image=f"portfolio/{slug}.webp",
        technologies=extra.pop("technologies", "Django, Tailwind"),
        **extra,
    )


class PublicPagesTests(TestCase):
    def test_main_pages_return_200(self):
        for name in ("home", "services", "skills", "portfolio", "blog", "contact", "search"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_skills_page_lists_backend_and_frontend_stack(self):
        html = self.client.get(reverse("skills")).content.decode()

        for tech in ("Rust", "Go", "TypeScript", "React", "Next.js", "Astro"):
            with self.subTest(tech=tech):
                self.assertIn(f">{tech}<", html)

    def test_home_exposes_skip_link_and_main_target(self):
        html = self.client.get(reverse("home")).content.decode()

        self.assertIn('href="#main-content"', html)
        self.assertIn('id="main-content"', html)

    def test_home_json_ld_search_action_targets_the_search_page(self):
        html = self.client.get(reverse("home")).content.decode()

        self.assertIn(reverse("search") + "?q={search_term_string}", html)
        self.assertNotIn("/blog/?q=", html)

    def test_seo_defaults_match_the_current_positioning(self):
        html = self.client.get(reverse("home")).content.decode()

        self.assertIn("Rust / Go", html)
        self.assertNotIn("infaillible", html)


class BlogTests(TestCase):
    def test_blog_lists_only_published_articles(self):
        _make_article("publie", title="Article publié")
        _make_article("brouillon", published=False, title="Article brouillon")

        response = self.client.get(reverse("blog"))

        self.assertContains(response, "Article publié")
        self.assertNotContains(response, "Article brouillon")

    def test_article_detail_ok_and_unpublished_is_404(self):
        _make_article("publie", title="Article publié")
        _make_article("brouillon", published=False)

        ok = self.client.get(reverse("article_detail", args=["publie"]))
        hidden = self.client.get(reverse("article_detail", args=["brouillon"]))

        self.assertEqual(ok.status_code, 200)
        self.assertContains(ok, "Article publié")
        self.assertEqual(hidden.status_code, 404)


class PortfolioTests(TestCase):
    def test_portfolio_and_project_detail(self):
        _make_project("alpha", title="Projet Alpha")

        listing = self.client.get(reverse("portfolio"))
        detail = self.client.get(reverse("project_detail", args=["alpha"]))
        missing = self.client.get(reverse("project_detail", args=["inconnu"]))

        self.assertContains(listing, "Projet Alpha")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(missing.status_code, 404)


class SearchTests(TestCase):
    def test_search_finds_articles_and_projects(self):
        _make_article("django-perf", title="Optimiser Django", summary="Requêtes SQL")
        _make_article("brouillon", published=False, title="Django secret")
        _make_project("shop", title="Boutique", technologies="Django, Redis")

        response = self.client.get(reverse("search"), {"q": "Django"})

        self.assertContains(response, "Optimiser Django")
        self.assertContains(response, "Boutique")
        self.assertNotContains(response, "Django secret")

    def test_search_without_query_returns_empty_page(self):
        response = self.client.get(reverse("search"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["articles"]), [])
        self.assertEqual(list(response.context["projects"]), [])


class SeoEndpointsTests(TestCase):
    def test_sitemap_lists_content_but_not_drafts(self):
        _make_article("publie")
        _make_article("brouillon", published=False)
        _make_project("alpha")

        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("/blog/publie/", body)
        self.assertIn("/portfolio/alpha/", body)
        self.assertNotIn("/blog/brouillon/", body)

    def test_robots_txt_points_to_sitemap_and_hides_admin(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].split(";")[0], "text/plain")
        body = response.content.decode()
        self.assertIn("Sitemap: https://horuservices.cloud/sitemap.xml", body)
        self.assertIn("Disallow: /admin-horus/", body)

    def test_rss_feed_lists_published_articles_only(self):
        _make_article("publie", title="Article publié")
        _make_article("brouillon", published=False, title="Article brouillon")

        response = self.client.get(reverse("article_feed"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Article publié")
        self.assertNotContains(response, "Article brouillon")


class ErrorPagesTests(TestCase):
    def test_custom_404_page(self):
        response = self.client.get("/cette-page-n-existe-pas/")

        self.assertContains(response, "Page introuvable", status_code=404)

    def test_500_page_is_standalone(self):
        """Rendue sans contexte : elle ne doit dependre ni de base.html ni de {% url %}."""
        response = server_error(RequestFactory().get("/"))

        self.assertEqual(response.status_code, 500)
        body = response.content.decode()
        self.assertIn("Erreur 500", body)
        self.assertIn('href="/contact/"', body)
        self.assertNotIn("{%", body)


class AdminSmokeTests(TestCase):
    """Garde-fou pour les montees de version (Django, django-unfold...)."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="mot-de-passe-de-test",
            first_name="Admin",
            last_name="Test",
        )
        _make_article("publie")
        _make_project("alpha")
        Contact.objects.create(name="Alice", email="alice@example.com", message="Bonjour")

    def test_admin_index_and_changelists_render(self):
        self.client.force_login(self.admin_user)

        urls = [reverse("admin:index")] + [
            reverse(f"admin:core_{model}_changelist")
            for model in ("article", "project", "contact", "customuser")
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_requires_login(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])


class LoggingConfigTests(SimpleTestCase):
    def test_disallowed_host_noise_is_silenced(self):
        logger = settings.LOGGING["loggers"]["django.security.DisallowedHost"]

        self.assertEqual(logger["handlers"], ["null"])
        self.assertFalse(logger["propagate"])

    def test_error_log_is_rotated(self):
        handler = settings.LOGGING["handlers"]["file"]

        self.assertTrue(handler["class"].endswith("RotatingFileHandler"))
        self.assertGreater(handler["backupCount"], 0)

    def test_unknown_host_is_rejected_with_400(self):
        response = self.client.get("/", HTTP_HOST="evil.example.org")

        self.assertEqual(response.status_code, 400)


class SelfHostedFontsTests(TestCase):
    """Les polices sont servies par le site : aucune requete vers Google Fonts."""

    def setUp(self):
        self.html = self.client.get(reverse("home")).content.decode()

    def test_no_request_to_google_fonts(self):
        self.assertNotIn("fonts.googleapis.com", self.html)
        self.assertNotIn("fonts.gstatic.com", self.html)

    def test_critical_latin_subsets_are_preloaded(self):
        for name in ("inter-latin-wght-normal", "plus-jakarta-sans-latin-wght-normal"):
            with self.subTest(font=name):
                self.assertRegex(
                    self.html,
                    rf'<link rel="preload" href="[^"]*{name}\.woff2" as="font" type="font/woff2" crossorigin>',
                )

    def test_every_declared_font_file_exists(self):
        urls = re.findall(r'url\("([^"]+\.woff2)"\)', self.html)

        self.assertGreaterEqual(len(urls), 4)  # 2 familles x (latin + latin-ext)
        for url in urls:
            with self.subTest(url=url):
                relative = url.removeprefix(settings.STATIC_URL)
                self.assertIsNotNone(finders.find(relative), f"fichier de police introuvable : {url}")

    def test_font_families_match_the_tailwind_theme(self):
        # input.css : --font-display / --font-body doivent pointer sur ces @font-face
        for family in ("Plus Jakarta Sans", "Inter"):
            with self.subTest(family=family):
                self.assertIn(f'font-family: "{family}"', self.html)
