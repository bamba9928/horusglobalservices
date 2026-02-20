from django import forms
import re
from .models import Contact


class ContactForm(forms.ModelForm):
    """Formulaire de contact stylisé avec Tailwind CSS"""

    class Meta:
        model = Contact
        fields = ["name", "email", "phone", "message"]
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

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return name

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 10:
            raise forms.ValidationError("Le message est un peu court (min. 10 caractères).")
        return message

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return ""

        # Utilisation de fullmatch pour une validation précise de la chaîne entière
        if not re.fullmatch(r"\+?[\d\s\-]{7,20}", phone):
            raise forms.ValidationError("Numéro de téléphone invalide.")
        return phone