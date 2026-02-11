from django import forms
from .models import Contact


class ContactForm(forms.ModelForm):
    """Formulaire de contact avec validation personnalisée"""

    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Jean Dupont',
                'autocomplete': 'name',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'jean@example.com',
                'autocomplete': 'email',
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+221 XX XXX XX XX',
                'autocomplete': 'tel',
            }),
            'message': forms.Textarea(attrs={
                'placeholder': 'Décrivez votre projet : type d\'application, fonctionnalités souhaitées, délais, budget estimé...',
                'rows': 6,
            }),
        }

    def clean_name(self):
        """Validation du nom"""
        name = self.cleaned_data.get('name')
        if len(name) < 2:
            raise forms.ValidationError("Le nom doit contenir au moins 2 caractères.")
        return name

    def clean_message(self):
        """Validation du message"""
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise forms.ValidationError("Le message doit contenir au moins 10 caractères.")
        return message