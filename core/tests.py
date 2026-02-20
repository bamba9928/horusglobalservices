from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from .forms import ContactForm
from .models import Contact


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