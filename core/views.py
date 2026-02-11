from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from .forms import ContactForm


def home(request):
    """Page d'accueil"""
    context = {
        'WHATSAPP_URL': settings.WHATSAPP_URL,
    }
    return render(request, 'core/home.html', context)


def services(request):
    """Page services détaillée"""
    context = {
        'WHATSAPP_URL': settings.WHATSAPP_URL,
    }
    return render(request, 'core/services.html', context)


def skills(request):
    """Page stack technique et compétences"""
    context = {
        'WHATSAPP_URL': settings.WHATSAPP_URL,
    }
    return render(request, 'core/skills.html', context)


def contact(request):
    """Page contact avec formulaire"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Sauvegarder le message
            contact = form.save()

            # Message de confirmation
            messages.success(
                request,
                f"Merci {contact.name} ! Votre message a bien été envoyé. "
                f"Je vous réponds sous 24h à {contact.email}."
            )

            # Redirection pour éviter la re-soumission
            return redirect('contact')
    else:
        form = ContactForm()

    context = {
        'form': form,
        'WHATSAPP_URL': settings.WHATSAPP_URL,
    }
    return render(request, 'core/contact.html', context)