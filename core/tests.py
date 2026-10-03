from pathlib import Path
from unittest.mock import patch

import importlib
import json
import re
import shutil
import sys
import tempfile
from html.parser import HTMLParser
from io import BytesIO, StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.core import mail
from django.core.management import CommandError, call_command
from django.core.cache import cache
from django.core.mail.backends.smtp import EmailBackend as SmtpEmailBackend
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.templatetags.static import static
from django.urls import clear_url_caches, reverse
from django.views.defaults import server_error

from PIL import Image

from django_ckeditor_5.fields import CKEditor5Field

from config.mailers import build_mailers

from .article_cleanup import clean_article_html
from .forms import ContactForm
from .models import Article, Contact, LegalPage, Project
from .views import MARQUEE_MIN_CARDS

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"

# Le formulaire de contact limite chaque IP a 5 envois par heure via le cache. Avec le
# FileBasedCache de la config, ce compteur survivait entre deux executions des tests
# (le 6e passage de la journee echouait) : cache en memoire, vide a chaque test.
LOCMEM_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


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


@override_settings(CACHES=LOCMEM_CACHE)
class ContactViewTests(TestCase):
    def setUp(self):
        cache.clear()

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
        self.assertIn("Disallow: /ckeditor5/", body)

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

    def test_admin_add_and_change_forms_render(self):
        self.client.force_login(self.admin_user)
        contact = Contact.objects.get()
        urls = [
            reverse("admin:core_article_add"), reverse("admin:core_project_add"),
            reverse("admin:core_legalpage_add"), reverse("admin:core_customuser_add"),
            reverse("admin:core_contact_change", args=[contact.pk]),
            reverse("admin:core_project_change", args=[Project.objects.get().pk]),
            reverse("admin:core_customuser_change", args=[self.admin_user.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_contact_admin_actions_update_the_flags(self):
        self.client.force_login(self.admin_user)
        contact = Contact.objects.get()
        url = reverse("admin:core_contact_changelist")

        for action, field in (("mark_as_read", "is_read"), ("mark_as_responded", "is_responded")):
            with self.subTest(action=action):
                response = self.client.post(url, {"action": action, "_selected_action": [contact.pk]})
                self.assertEqual(response.status_code, 302)
                contact.refresh_from_db()
                self.assertTrue(getattr(contact, field))

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


def _png_upload(name="photo.png", content_type="image/png"):
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class CKEditor5Tests(TestCase):
    """CKEditor 5 remplace CKEditor 4 (fin de vie) : champs, admin, envoi d'images."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.staff = user_model.objects.create_superuser(
            email="staff@example.com", password="mot-de-passe-de-test", first_name="S", last_name="T"
        )
        cls.visitor = user_model.objects.create_user(
            email="visiteur@example.com", password="mot-de-passe-de-test"
        )

    def test_rich_text_fields_use_ckeditor5(self):
        for model in (Article, LegalPage):
            with self.subTest(model=model.__name__):
                self.assertIsInstance(model._meta.get_field("content"), CKEditor5Field)

    def test_ckeditor4_is_not_installed_anymore(self):
        self.assertNotIn("ckeditor", settings.INSTALLED_APPS)
        self.assertNotIn("ckeditor_uploader", settings.INSTALLED_APPS)
        self.assertIn("django_ckeditor_5", settings.INSTALLED_APPS)

    def test_heading_options_keep_h1_to_h3_used_by_existing_articles(self):
        views = {o["view"] for o in settings.CKEDITOR_5_CONFIGS["default"]["heading"]["options"] if "view" in o}

        self.assertLessEqual({"h1", "h2", "h3"}, views)

    def test_admin_forms_load_the_editor(self):
        article = _make_article("existant")
        self.client.force_login(self.staff)

        for url in (
            reverse("admin:core_article_add"),
            reverse("admin:core_article_change", args=[article.pk]),
            reverse("admin:core_legalpage_add"),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "django_ckeditor_5/dist/bundle.js")
                self.assertContains(response, 'class="django_ckeditor_5"')
                self.assertContains(response, "django_ckeditor_5/dist/translations/fr.js")
                self.assertContains(response, settings.CKEDITOR_5_CUSTOM_CSS)

    def test_dark_theme_stylesheet_exists_and_themes_the_content_text(self):
        path = finders.find(settings.CKEDITOR_5_CUSTOM_CSS)

        self.assertIsNotNone(path, "feuille de style du theme sombre introuvable")
        css = Path(path).read_text(encoding="utf-8")
        # --ck-content-font-color vaut #000 par defaut : sans cette surcharge, texte noir sur fond sombre
        self.assertIn("html.dark", css)
        self.assertIn("--ck-content-font-color", css)

    def test_legal_pages_can_now_be_managed_from_the_admin(self):
        self.client.force_login(self.staff)

        self.assertEqual(self.client.get(reverse("admin:core_legalpage_changelist")).status_code, 200)

    def test_saving_an_article_from_the_admin_keeps_the_html(self):
        self.client.force_login(self.staff)
        html = '<h2>Titre</h2><p style="text-align:center;">Bonjour <strong>monde</strong></p>'

        response = self.client.post(
            reverse("admin:core_article_add"),
            {"title": "Nouvel article", "slug": "nouvel-article", "summary": "Resume", "category": "news",
             "content": html, "created_at_0": "2026-10-03", "created_at_1": "10:00:00", "is_published": "on"},
        )

        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        self.assertEqual(Article.objects.get(slug="nouvel-article").content, html)

    def test_upload_is_refused_to_visitors_and_anonymous_users(self):
        url = reverse("ck_editor_5_upload_file")
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            anonymous = self.client.post(url, {"upload": _png_upload()})
            self.client.force_login(self.visitor)
            visitor = self.client.post(url, {"upload": _png_upload()})

        self.assertEqual(anonymous.status_code, 403)
        self.assertEqual(visitor.status_code, 403)

    def test_staff_can_upload_an_image_into_dated_uploads_folder(self):
        self.client.force_login(self.staff)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(reverse("ck_editor_5_upload_file"), {"upload": _png_upload()})
            self.assertEqual(response.status_code, 200)
            url = response.json()["url"]
            self.assertRegex(url, r"^/media/uploads/\d{4}/\d{2}/photo[\w]*\.png$")
            saved = Path(media) / url.removeprefix("/media/")
            self.assertTrue(saved.is_file())
            Image.open(saved).verify()

    def test_upload_rejects_non_image_extension_and_fake_images(self):
        self.client.force_login(self.staff)
        url = reverse("ck_editor_5_upload_file")
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            wrong_type = self.client.post(url, {"upload": SimpleUploadedFile("notes.txt", b"hello")})
            fake_png = self.client.post(url, {"upload": SimpleUploadedFile("faux.png", b"<script>alert(1)</script>")})
            svg = self.client.post(url, {"upload": SimpleUploadedFile("logo.svg", b"<svg onload=alert(1)/>")})
            leftovers = [p for p in Path(media).rglob("*") if p.is_file()]

        for response in (wrong_type, fake_png, svg):
            self.assertEqual(response.status_code, 400)
        self.assertEqual(leftovers, [])

    def test_upload_path_traversal_is_neutralized(self):
        self.client.force_login(self.staff)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post(
                reverse("ck_editor_5_upload_file"), {"upload": _png_upload("../../evil.png")}
            )
            self.assertEqual(response.status_code, 200)
            url = response.json()["url"]
            self.assertNotIn("..", url)
            self.assertTrue((Path(media) / url.removeprefix("/media/")).resolve().is_relative_to(Path(media).resolve()))

    def test_public_article_renders_ckeditor5_markup(self):
        content = (
            '<figure class="image image-style-align-left"><img src="/media/uploads/2026/10/a.png" alt="Schema">'
            "<figcaption>Légende</figcaption></figure>"
            '<pre><code class="language-python">print("ok")</code></pre>'
            '<figure class="table"><table><tbody><tr><td>A</td><td>B</td></tr></tbody></table></figure>'
        )
        _make_article("riche", content=content)

        html = self.client.get(reverse("article_detail", args=["riche"])).content.decode()

        for fragment in ('class="image image-style-align-left"', 'class="language-python"', '<figure class="table">', "Légende"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, html)


class MailersConfigTests(SimpleTestCase):
    """Django 6.1 : MAILERS remplace EMAIL_HOST & co (depreciés). Memes variables d'environnement."""

    PROD_ENV = {
        "EMAIL_HOST": "smtp.example.org", "EMAIL_PORT": "465", "EMAIL_USE_TLS": "False",
        "EMAIL_HOST_USER": "robot", "EMAIL_HOST_PASSWORD": "secret", "EMAIL_TIMEOUT": "7",
    }

    def test_debug_prints_emails_to_the_console(self):
        mailers = build_mailers(True, {})

        self.assertEqual(mailers["default"]["BACKEND"], "django.core.mail.backends.console.EmailBackend")

    def test_production_reads_the_same_environment_variables_as_before(self):
        mailer = build_mailers(False, self.PROD_ENV)["default"]

        self.assertEqual(mailer["BACKEND"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual(
            mailer["OPTIONS"],
            {"host": "smtp.example.org", "port": 465, "use_tls": False,
             "username": "robot", "password": "secret", "timeout": 7},
        )

    def test_defaults_are_those_of_the_previous_settings(self):
        options = build_mailers(False, {})["default"]["OPTIONS"]

        self.assertEqual(
            options,
            {"host": "smtp.sendgrid.net", "port": 587, "use_tls": True,
             "username": "", "password": "", "timeout": 20},
        )

    def test_options_are_accepted_by_the_smtp_backend(self):
        # Meme chemin que send_mail() : mail.mailers[alias] (instancier le backend a la main
        # est deprecie en 6.1). Aucune connexion n'est ouverte tant qu'on n'envoie rien.
        with override_settings(MAILERS=build_mailers(False, self.PROD_ENV)):
            backend = mail.mailers["default"]

        self.assertIsInstance(backend, SmtpEmailBackend)
        self.assertEqual((backend.host, backend.port, backend.username, backend.use_tls, backend.timeout),
                         ("smtp.example.org", 465, "robot", False, 7))

    def test_project_settings_define_mailers_and_no_deprecated_email_settings(self):
        self.assertTrue(hasattr(__import__("config.settings", fromlist=["MAILERS"]), "MAILERS"))
        raw = Path(settings.BASE_DIR, "config", "settings.py").read_text(encoding="utf-8")
        for name in ("EMAIL_BACKEND", "EMAIL_HOST ", "EMAIL_PORT", "EMAIL_USE_TLS", "EMAIL_HOST_USER",
                     "EMAIL_HOST_PASSWORD", "EMAIL_TIMEOUT"):
            with self.subTest(setting=name):
                self.assertNotRegex(raw, rf"^{name}\s*=", "reglage deprecie reapparu")


@override_settings(CACHES=LOCMEM_CACHE)
class ContactMailDeliveryTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_contact_form_sends_the_notification_through_the_mailers(self):
        response = self.client.post(
            reverse("contact"),
            {"name": "Alice Ndiaye", "email": "alice@example.com", "phone": "+221771234567",
             "message": "Bonjour, je souhaite un devis pour une application."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertIn("Alice Ndiaye", message.subject)
        self.assertEqual(message.to, [settings.PUBLIC_EMAIL])
        self.assertEqual(message.from_email, settings.DEFAULT_FROM_EMAIL)


class _InlineCodeScanner(HTMLParser):
    """Releve les <script>/<style> en ligne (hors JSON-LD) et les attributs on*= d'une page."""

    def __init__(self):
        super().__init__()
        self.script_nonces, self.style_nonces, self.handlers = [], [], []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.handlers += [(tag, name) for name in attributes if name.startswith("on")]
        if tag == "script" and "src" not in attributes and attributes.get("type") != "application/ld+json":
            self.script_nonces.append(attributes.get("nonce"))
        if tag == "style":
            self.style_nonces.append(attributes.get("nonce"))


def _directives(policy):
    return {part.split()[0]: part.split()[1:] for part in policy.split(";") if part.strip()}


class ContentSecurityPolicyTests(TestCase):
    """CSP stricte a nonce sur le site public (core/middleware.py)."""

    @classmethod
    def setUpTestData(cls):
        _make_article("a")
        _make_project("p")
        LegalPage.objects.create(title="mentions-legales", slug="mentions-legales", content="<p>Mentions</p>")

    def public_urls(self):
        return [
            reverse("home"), reverse("services"), reverse("skills"), reverse("portfolio"), reverse("blog"),
            reverse("contact"), reverse("search") + "?q=django", reverse("article_detail", args=["a"]),
            reverse("project_detail", args=["p"]), reverse("legal_page", args=["mentions-legales"]),
            "/page-introuvable/",
        ]

    def test_public_pages_send_a_strict_nonce_based_policy(self):
        for url in self.public_urls():
            with self.subTest(url=url):
                policy = _directives(self.client.get(url)["Content-Security-Policy"])
                self.assertEqual(policy["default-src"], ["'self'"])
                self.assertEqual(policy["object-src"], ["'none'"])
                self.assertEqual(policy["base-uri"], ["'self'"])
                self.assertEqual(policy["form-action"], ["'self'"])
                self.assertEqual(policy["frame-ancestors"], ["'none'"])
                for directive in ("script-src", "style-src"):
                    sources = policy[directive]
                    self.assertEqual(sources[0], "'self'")
                    self.assertRegex(sources[1], r"^'nonce-[\w-]{16,}'$")
                    self.assertNotIn("'unsafe-inline'", sources)
                    self.assertNotIn("'unsafe-eval'", sources)
                # Tiers autorises = Google Analytics, et RIEN d'autre. Cloudflare Web Analytics n'a
                # besoin d'aucun hote ici : son script porte le nonce et il envoie ses mesures vers
                # /cdn-cgi/rum sur notre propre domaine ('self').
                hosts = {
                    name: {src for src in sources if re.match(r"https?://", src)}
                    for name, sources in policy.items()
                }
                self.assertEqual(hosts.pop("script-src"), {"https://www.googletagmanager.com"})
                self.assertEqual(
                    hosts.pop("connect-src"),
                    {"https://*.google-analytics.com", "https://*.analytics.google.com", "https://*.googletagmanager.com"},
                )
                self.assertEqual({name: h for name, h in hosts.items() if h}, {}, "hote tiers inattendu")

    def test_every_inline_script_and_style_carries_the_request_nonce(self):
        for url in self.public_urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                nonce = re.search(r"'nonce-([\w-]+)'", response["Content-Security-Policy"]).group(1)
                scanner = _InlineCodeScanner()
                scanner.feed(response.content.decode())

                self.assertEqual(set(scanner.script_nonces) - {nonce}, set(), "script en ligne sans le bon nonce")
                self.assertEqual(set(scanner.style_nonces) - {nonce}, set(), "style en ligne sans le bon nonce")

    def test_inline_code_is_actually_present_so_the_check_is_meaningful(self):
        scanner = _InlineCodeScanner()
        scanner.feed(self.client.get(reverse("home")).content.decode())

        self.assertGreaterEqual(len(scanner.script_nonces), 3)  # GA, navigation, bandeau cookies
        self.assertGreaterEqual(len(scanner.style_nonces), 3)

    def test_no_inline_event_handlers_in_public_pages(self):
        for url in self.public_urls():
            with self.subTest(url=url):
                scanner = _InlineCodeScanner()
                scanner.feed(self.client.get(url).content.decode())

                self.assertEqual(scanner.handlers, [], "attribut on*= en ligne : bloque par la CSP, utiliser addEventListener")

    def test_nonce_is_different_on_every_request(self):
        nonces = {
            re.search(r"'nonce-([\w-]+)'", self.client.get(reverse("home"))["Content-Security-Policy"]).group(1)
            for _ in range(5)
        }

        self.assertEqual(len(nonces), 5)

    def test_admin_and_non_html_responses_are_left_alone(self):
        for url in (reverse("admin:login"), "/robots.txt", "/sitemap.xml", reverse("article_feed")):
            with self.subTest(url=url):
                self.assertNotIn("Content-Security-Policy", self.client.get(url))

    def test_report_only_mode_does_not_enforce(self):
        with override_settings(CSP_REPORT_ONLY=True):
            response = self.client.get(reverse("home"))

        self.assertIn("Content-Security-Policy-Report-Only", response)
        self.assertNotIn("Content-Security-Policy", response)

    def test_kill_switch_and_debug_disable_the_policy(self):
        for overrides in ({"CSP_ENABLED": False}, {"DEBUG": True}):
            with self.subTest(overrides=overrides), override_settings(**overrides):
                response = self.client.get(reverse("home"))
                self.assertNotIn("Content-Security-Policy", response)
                self.assertNotIn("nonce-", response.content.decode().split("<body")[0][:5000])

    def test_nginx_reference_policy_allows_the_same_analytics_hosts(self):
        """nginx pose sa propre CSP en plus : les deux s'additionnent, GA n'est autorise que si les DEUX le permettent."""
        raw = Path(settings.BASE_DIR, "nginx").read_text(encoding="utf-8")
        nginx_policy = _directives(re.search(r'add_header Content-Security-Policy "([^"]+)"', raw).group(1))

        for host in settings.CSP_GOOGLE_ANALYTICS_SCRIPT_SRC + settings.CSP_CLOUDFLARE_ANALYTICS_SCRIPT_SRC:
            self.assertIn(host, nginx_policy["script-src"])
        # Tout ce que Django autorise en connect-src doit l'etre aussi cote nginx (intersection)
        for host in settings.CSP_DIRECTIVES["connect-src"]:
            self.assertIn(host, nginx_policy["connect-src"])
        # La balise Cloudflare envoie ses mesures a notre domaine : aucun hote Cloudflare en connect-src
        self.assertFalse([h for h in nginx_policy["connect-src"] if "cloudflare" in h])

    def test_google_analytics_only_loads_after_cookie_consent(self):
        """Conformite : aucune requete vers Google tant que l'utilisateur n'a pas clique Accepter."""
        html = self.client.get(reverse("home")).content.decode()
        scripts = re.findall(r"<script nonce=[^>]*>(.*?)</script>", html, re.S)
        loaders = [code for code in scripts if "googletagmanager.com/gtag/js" in code]

        self.assertEqual(len(loaders), 2)  # chargeur de l'en-tete (visiteur deja consentant) + bandeau cookies
        head_loader = next(code for code in loaders if "cookie-banner" not in code)
        # le chargeur de l'en-tete sort AVANT tout chargement si le consentement n'est pas "accepted"
        guard = head_loader.index("localStorage.getItem('cookie_consent') !== 'accepted'")
        self.assertLess(guard, head_loader.index("googletagmanager.com"))
        self.assertIn("return;", head_loader[guard:guard + 120])
        # dans le bandeau, loadGA() n'est appele que par le clic sur Accepter
        banner = next(code for code in loaders if "cookie-banner" in code)
        calls = [m.start() for m in re.finditer(r"loadGA\(\);", banner)]
        self.assertEqual(len(calls), 1)
        self.assertGreater(calls[0], banner.index("getElementById('cookie-accept')"))
        self.assertLess(calls[0], banner.index("getElementById('cookie-reject')"))

    @override_settings(ROOT_URLCONF="core.test_urls")
    def test_server_error_page_gets_its_own_minimal_policy(self):
        client = Client(raise_request_exception=False)

        with self.assertLogs("django.request", level="ERROR"):
            response = client.get("/boom/")

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "Erreur 500", status_code=500)
        policy = _directives(response["Content-Security-Policy"])
        self.assertEqual(policy["default-src"], ["'none'"])
        self.assertEqual(policy["style-src"], ["'unsafe-inline'"])  # <style> de templates/500.html
        self.assertNotIn("script-src", policy)


PRODUCTION_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


class VersionedStaticFilesTests(TestCase):
    """Production : fichiers statiques a empreinte (app.<hash>.js).

    nginx et Cloudflare servent /static/ en cache immutable 30 jours : sans empreinte dans le nom,
    la montee d'Unfold 0.80 -> 0.108 a laisse l'admin charger d'anciens CSS/JS (adminTheme is not
    defined...). Ces tests rejouent le collectstatic du deploiement avec le stockage de production.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.static_root = tempfile.mkdtemp()
        cls._override = override_settings(STORAGES=PRODUCTION_STORAGES, STATIC_ROOT=cls.static_root)
        cls._override.enable()
        call_command("collectstatic", interactive=False, verbosity=0, clear=True)

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls.static_root, ignore_errors=True)
        super().tearDownClass()

    def test_collectstatic_succeeds_and_writes_a_manifest(self):
        self.assertTrue((Path(self.static_root) / "staticfiles.json").is_file())

    def test_static_urls_carry_a_content_hash(self):
        for name in (
            "unfold/js/app.js", "unfold/css/styles.css", "css/output.css",
            "fonts/inter-latin-wght-normal.woff2", "django_ckeditor_5/dist/bundle.js", "css/ckeditor-admin.v1.css",
        ):
            with self.subTest(name=name):
                stem, dot, extension = name.rpartition(".")
                self.assertRegex(static(name), rf"^/static/{re.escape(stem)}\.[0-9a-f]{{12}}\.{extension}$")

    def test_tailwind_source_files_are_not_published(self):
        # `@import "tailwindcss"` n'est pas une reference CSS : il ferait echouer collectstatic
        self.assertEqual(list(Path(self.static_root).rglob("input*.css")), [])

    def test_pages_only_reference_static_files_that_exist(self):
        for url in (reverse("home"), reverse("contact"), reverse("admin:login")):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                referenced = set(re.findall(r'(?:src|href)="(/static/[^"?]+)', html))

                self.assertTrue(referenced)
                for path in referenced:
                    self.assertTrue(
                        (Path(self.static_root) / path.removeprefix("/static/")).is_file(), f"fichier manquant : {path}"
                    )
                    # versionne : nom de la forme nom.<12 hex>.ext
                    self.assertRegex(path, r"\.[0-9a-f]{12}\.[a-z0-9]+$", f"URL non versionnee : {path}")

    def test_obsolete_staticfiles_storage_setting_is_gone(self):
        raw = Path(settings.BASE_DIR, "config", "settings.py").read_text(encoding="utf-8")

        self.assertNotRegex(raw, r"^STATICFILES_STORAGE\s*=")


class UrlconfImportTests(SimpleTestCase):
    def test_urlconf_import_does_not_need_collected_static_files(self):
        """deploy.sh lance `migrate` (qui charge les URL) AVANT `collectstatic` : l'import de config.urls
        ne doit donc pas lire le manifeste des statiques (ancien bug : ValueError sur favicon.ico)."""
        original = sys.modules["config.urls"]
        with tempfile.TemporaryDirectory() as empty_root, override_settings(
            STORAGES=PRODUCTION_STORAGES, STATIC_ROOT=empty_root
        ):
            try:
                del sys.modules["config.urls"]
                clear_url_caches()
                importlib.import_module("config.urls")
            finally:
                sys.modules["config.urls"] = original
                clear_url_caches()


class ArticleCleanupTests(TestCase):
    """Nettoyage des <h1> des anciens articles (core/article_cleanup.py)."""

    TITLE = "Deployer une application Django"

    def test_duplicate_title_is_removed_but_only_when_it_is_the_first_heading(self):
        html = "<h1>Deployer une application Django</h1><h2>Intro</h2><p>Texte</p>"

        cleaned, changes = clean_article_html(html, self.TITLE)

        self.assertEqual(cleaned, "<h2>Intro</h2><p>Texte</p>")
        self.assertEqual(changes["titre en double supprimé"], 1)

    def test_section_h1_become_h2_and_sentences_become_paragraphs(self):
        html = (
            "<h1>Le deploiement d'une application est une etape critique. Une mauvaise conf.</h1>"
            '<h1 style="text-align:center;">1. Preparer le serveur</h1><h3>Sous-section</h3>'
        )

        cleaned, changes = clean_article_html(html, self.TITLE)

        self.assertIn("<p>Le deploiement d'une application est une etape critique. Une mauvaise conf.</p>", cleaned)
        self.assertIn('<h2 style="text-align:center;">1. Preparer le serveur</h2>', cleaned)  # attributs conserves
        self.assertIn("<h3>Sous-section</h3>", cleaned)  # les h3 ne bougent pas
        self.assertEqual(changes["h1 → paragraphe (phrase)"], 1)
        self.assertEqual(changes["h1 → h2 (titre de section)"], 1)

    def test_empty_headings_and_spacer_paragraphs_are_removed(self):
        html = "<h1>&nbsp;</h1><h2></h2><p>&nbsp;</p><p><br /></p><p>Vrai texte</p><h3>  </h3>"

        cleaned, changes = clean_article_html(html, self.TITLE)

        self.assertEqual(cleaned, "<p>Vrai texte</p>")
        self.assertEqual(changes["titre vide supprimé"], 3)
        self.assertEqual(changes["paragraphe vide supprimé"], 2)

    def test_text_content_is_never_altered(self):
        html = "<h1>Titre A</h1><p>Un <strong>texte</strong> &amp; du <code>code</code></p><h1>Titre B</h1><pre>x = 1</pre>"

        cleaned, _ = clean_article_html(html, self.TITLE)

        def words(fragment):
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment)).split()

        self.assertEqual(words(cleaned), words(html))

    def test_cleanup_is_idempotent_and_leaves_well_formed_articles_alone(self):
        html = "<h2>Intro</h2><p>Texte</p><ul><li>a</li></ul><pre><code>x</code></pre>"
        messy = "<h1>Deployer une application Django</h1><h1>1. Etape</h1><p>&nbsp;</p><p>Texte</p>"

        self.assertEqual(clean_article_html(html, self.TITLE), (html, {}))
        once, _ = clean_article_html(messy, self.TITLE)
        self.assertEqual(clean_article_html(once, self.TITLE), (once, {}))

    def test_command_simulates_by_default_and_requires_a_backup_to_write(self):
        article = _make_article("sale", title=self.TITLE, content="<h1>1. Etape</h1><p>Texte</p>")
        out = tempfile.mkdtemp()

        call_command("clean_article_headings", stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.content, "<h1>1. Etape</h1><p>Texte</p>")  # simulation : rien d'ecrit
        with self.assertRaises(CommandError):
            call_command("clean_article_headings", apply=True, stdout=StringIO())

        backup = Path(out) / "sauvegarde.json"
        call_command("clean_article_headings", apply=True, backup=str(backup), stdout=StringIO())
        article.refresh_from_db()
        self.assertEqual(article.content, "<h2>1. Etape</h2><p>Texte</p>")
        saved = json.loads(backup.read_text(encoding="utf-8"))
        self.assertEqual(saved[0]["content"], "<h1>1. Etape</h1><p>Texte</p>")  # contenu ORIGINAL sauvegarde
        shutil.rmtree(out, ignore_errors=True)


class ArticleTypographyTests(TestCase):
    """Les classes `prose` des templates ne servent a rien sans le plugin Typography compile dans output.css."""

    def test_compiled_css_contains_the_typography_rules(self):
        css = Path(settings.BASE_DIR, "static", "css", "output.css").read_text(encoding="utf-8")

        self.assertGreater(css.count(".prose"), 100)
        self.assertIn(".prose-invert", css)
        # citations sans guillemets automatiques (encadres d'avertissement)
        self.assertRegex(css, r"\.prose blockquote p:first-of-type::?before[^{]*\{content:none\}")

    def test_legal_page_uses_the_dark_variant(self):
        """Sans prose-invert, le plugin donne du texte gris fonce illisible sur le fond sombre du site."""
        LegalPage.objects.create(title="cookies", slug="cookies", content="<h2>Cookies</h2><p>Texte</p>")

        html = self.client.get(reverse("legal_page", args=["cookies"])).content.decode()

        self.assertRegex(html, r'class="prose prose-invert[^"]*"')

    def test_article_page_keeps_the_dark_variant_and_blockquote_styling(self):
        _make_article("a", content="<blockquote><p>Citation</p></blockquote>")

        html = self.client.get(reverse("article_detail", args=["a"])).content.decode()

        self.assertIn("prose-invert", html)
        self.assertIn("prose-blockquote:not-italic", html)
