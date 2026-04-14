from django import forms
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.utils import timezone
import re

from .models import Contact


# Blacklist simple (tu peux déplacer en settings.py plus tard)
BLOCKED_EMAILS = {
    "zekisuquc419@gmail.com",
}

BLOCKED_DOMAINS = {
    # Domaines jetables / temporaires
    "tempmail.com",
    "10minutemail.com",
    "mailinator.com",
    "guerrillamail.com",
    "throwaway.email",
    "yopmail.com",
    "trashmail.com",
    "dispostable.com",
    "maildrop.cc",
    "sharklasers.com",
    "guerrillamailblock.com",
    "grr.la",
    "tempail.com",
    "temp-mail.org",
    "fakeinbox.com",
    "mohmal.com",
    "getnada.com",
    "emailondeck.com",
    "33mail.com",
    "mailnesia.com",
    "mintemail.com",
    "tempr.email",
    "discard.email",
    "mailcatch.com",
    "harakirimail.com",
}

# Rate limiting : max de soumissions par IP
RATE_LIMIT_MAX = 5  # max 5 soumissions
RATE_LIMIT_WINDOW = 3600  # par heure (en secondes)


def _get_client_ip(request):
    """Récupère l'IP client (proxy-aware)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


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

        # Rejeter les noms contenant des chiffres ou caractères suspects
        if re.search(r"\d", name):
            raise forms.ValidationError("Le nom ne doit pas contenir de chiffres.")

        # Rejeter les noms avec trop de caractères spéciaux (spam typique)
        special_count = len(re.findall(r"[^a-zA-ZÀ-ÿ\s\-']", name))
        if special_count > 1:
            raise forms.ValidationError("Le nom contient des caractères non autorisés.")

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

            # Rejeter les emails avec trop de chiffres (souvent générés par bots)
            local_part = email.split("@")[0]
            digit_count = sum(1 for c in local_part if c.isdigit())
            if len(local_part) > 3 and digit_count > len(local_part) * 0.6:
                raise ValidationError("Adresse email non autorisée.")

        return email

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Le message est un peu court (min. 10 caractères).")

        # Heuristiques anti-spam
        lower_msg = message.lower()

        spam_keywords = [
            "crypto", "bitcoin", "ethereum", "nft", "blockchain",
            "casino", "poker", "betting", "gambling",
            "loan", "forex", "trading", "investment opportunity",
            "seo service", "seo optimization", "backlink",
            "whatsapp", "telegram",
            "viagra", "cialis", "pharmacy", "diet pill",
            "click here", "buy now", "free money", "earn money",
            "make money online", "work from home", "passive income",
            "nigerian prince", "lottery winner",
            "cheap followers", "buy followers", "instagram followers",
        ]
        if any(keyword in lower_msg for keyword in spam_keywords):
            raise forms.ValidationError("Message détecté comme spam.")

        # Trop de liens => suspect
        links_count = len(re.findall(r"https?://|www\.", lower_msg))
        if links_count >= 2:
            raise forms.ValidationError("Trop de liens dans le message.")

        # Détection de caractères répétitifs (ex: "aaaaaa", "!!!!!!")
        if re.search(r"(.)\1{5,}", message):
            raise forms.ValidationError("Message détecté comme spam.")

        # Trop de majuscules (cri / spam)
        alpha_chars = [c for c in message if c.isalpha()]
        if len(alpha_chars) > 20:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio > 0.7:
                raise forms.ValidationError("Évitez d'écrire en majuscules.")

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

        # Rate limiting par IP
        if self.request:
            ip = _get_client_ip(self.request)
            cache_key = f"contact_rate_{ip}"
            submissions = cache.get(cache_key, 0)
            if submissions >= RATE_LIMIT_MAX:
                raise ValidationError(
                    "Trop de soumissions. Veuillez réessayer plus tard."
                )
            cache.set(cache_key, submissions + 1, RATE_LIMIT_WINDOW)

        # Vérification "soumission trop rapide"
        started_at = (cleaned_data.get("form_started_at") or "").strip()
        if started_at:
            try:
                started_ts = float(started_at)
                now_ts = timezone.now().timestamp()
                elapsed = now_ts - started_ts

                # Si soumis en moins de 3 secondes => suspect
                if elapsed < 3:
                    raise ValidationError("Soumission trop rapide. Veuillez réessayer.")
            except (TypeError, ValueError):
                pass

        return cleaned_data