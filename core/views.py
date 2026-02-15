from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
import logging

from .forms import ContactForm
from .models import Article, Project

logger = logging.getLogger(__name__)


def home(request):
    """Page d'accueil"""
    recent_articles = Article.objects.filter(is_published=True)[:3]
    featured_projects = Project.objects.filter(is_featured=True)[:3]

    return render(request, 'core/home.html', {
        'recent_articles': recent_articles,
        'featured_projects': featured_projects,
    })


def services(request):
    return render(request, 'core/services.html')


def skills(request):
    return render(request, 'core/skills.html')


def blog(request):
    articles = Article.objects.filter(is_published=True)
    return render(request, 'core/blog.html', {'articles': articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, 'core/article_detail.html', {'article': article})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # 1) Sauvegarde dans la base de données (Admin)
            contact_obj = form.save()

            # 2) Envoi de l'email de notification à VOUS (Admin)
            subject = f"Nouveau contact de {contact_obj.name} - Horus Global"
            message = f"""
Nouveau message reçu depuis le site :

Nom : {contact_obj.name}
Email : {contact_obj.email}
Téléphone : {contact_obj.phone}

Message :
{contact_obj.message}
""".strip()

            # On envoie l'email (fail_silently retiré) + log propre
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.PUBLIC_EMAIL],
                )
            except Exception as e:
                logger.error("Erreur envoi email contact : %s", e, exc_info=True)

            messages.success(
                request,
                f"Merci {contact_obj.name} ! Votre message a bien été envoyé."
            )
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})


def portfolio(request):
    """Page Portfolio avec pagination"""
    projects_list = Project.objects.all()
    paginator = Paginator(projects_list, 9)

    page_number = request.GET.get('page')
    projects = paginator.get_page(page_number)

    return render(request, 'core/portfolio.html', {'projects': projects})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(request, 'core/project_detail.html', {'project': project})
