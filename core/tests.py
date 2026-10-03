from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .forms import ContactForm
from .models import Contact, Project
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
