from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import re

from .models import Contact


# Blacklist simple (tu peux déplacer en settings.py plus tard)
BLOCKED_EMAILS = {
    "zekisuquc419@gmail.com",
}

BLOCKED_DOMAINS = {
    # Exemples temporaires / spam fréquents (à adapter)
    "tempmail.com",
    "10minutemail.com",
    "mailinator.com",
    "guerrillamail.com",
}


class ContactForm(forms.ModelForm):
    """Formulaire de contact stylisé avec Tailwind CSS + anti-spam"""

    # Honeypot (champ caché)
    website = forms.CharField(required=False)

    # Timestamp pour vérifier si la soumission est trop rapide
    form_started_at = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Contact
        fields = ["name", "email", "phone", "message"]  # on garde seulement les champs du modèle
        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Jean Dupont",
                "autocomplete": "name",
                "class": "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white transition-all"
            }),
            "email": forms.EmailInput(attrs={
                "placeholder": "jean@example.com",
                "autocomplete": "email",
                "class": "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white transition-all"
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "+221 77 123 45 67",
                "autocomplete": "tel",
                "class": "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white transition-all"
            }),
            "message": forms.Textarea(attrs={
                "placeholder": "Décrivez votre projet : type d'application, fonctionnalités souhaitées, délais...",
                "rows": 5,
                "class": "w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-white focus:ring-1 focus:ring-white transition-all resize-none"
            }),
        }

    def __init__(self, *args, **kwargs):
        """
        Tu peux passer request si tu veux (utile pour logs / IP plus tard) :
        form = ContactForm(request.POST or None, request=request)
        """
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        # Honeypot rendu invisible sans casser le backend
        self.fields["website"].widget = forms.TextInput(attrs={
            "tabindex": "-1",
            "autocomplete": "off",
            "style": "position:absolute;left:-9999px;opacity:0;height:0;width:0;",
            "aria-hidden": "true",
        })

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return name

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()

        # Blocage email exact
        if email in BLOCKED_EMAILS:
            raise ValidationError("Adresse email non autorisée.")

        # Blocage domaine
        if "@" in email:
            domain = email.split("@")[-1]
            if domain in BLOCKED_DOMAINS:
                raise ValidationError("Domaine email non autorisé.")

        return email

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Le message est un peu court (min. 10 caractères).")

        # Heuristiques anti-spam basiques (tu peux ajuster)
        lower_msg = message.lower()

        spam_keywords = [
            "crypto",
            "bitcoin",
            "casino",
            "loan",
            "seo service",
            "whatsapp",
            "telegram",
        ]
        if any(keyword in lower_msg for keyword in spam_keywords):
            raise forms.ValidationError("Message détecté comme spam.")

        # Trop de liens => suspect
        links_count = len(re.findall(r"https?://|www\.", lower_msg))
        if links_count >= 2:
            raise forms.ValidationError("Trop de liens dans le message.")

        return message

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        # Validation précise de la chaîne entière
        if not re.fullmatch(r"\+?[\d\s\-]{7,20}", phone):
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return phone

    def clean_website(self):
        """Honeypot : si rempli, très probable bot."""
        value = (self.cleaned_data.get("website") or "").strip()
        if value:
            raise ValidationError("Spam détecté.")
        return value

    def clean(self):
        cleaned_data = super().clean()

        # Vérification "soumission trop rapide"
        started_at = (cleaned_data.get("form_started_at") or "").strip()
        if started_at:
            try:
                started_ts = float(started_at)
                now_ts = timezone.now().timestamp()
                elapsed = now_ts - started_ts

                # Si soumis en moins de 2 secondes => suspect
                if elapsed < 2:
                    raise ValidationError("Soumission trop rapide. Veuillez réessayer.")
            except (TypeError, ValueError):
                # Si valeur invalide, on ignore (ne pas casser UX)
                pass

        return cleaned_data