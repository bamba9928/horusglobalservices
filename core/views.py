import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator

from .forms import ContactForm
from .models import Article, Project

logger = logging.getLogger(__name__)

# Constantes pour la clarté du code
AUDIT_REQUEST_TYPE = "audit"
AUDIT_PREFILL_MESSAGE = (
    "Bonjour, je souhaiterais obtenir un audit complet "
    "(performance, SQL, sécurité) pour mon projet."
)


def home(request):
    """Page d'accueil"""
    recent_articles = Article.objects.filter(is_published=True)[:3]
    featured_projects = Project.objects.filter(is_featured=True)[:3]

    return render(request, "core/home.html", {
        "recent_articles": recent_articles,
        "featured_projects": featured_projects,
    })


def services(request):
    return render(request, "core/services.html")


def skills(request):
    return render(request, "core/skills.html")


def blog(request):
    articles = Article.objects.filter(is_published=True)
    return render(request, "core/blog.html", {"articles": articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, "core/article_detail.html", {"article": article})


def contact(request):
    # Récupération du type de demande (GET pour l'affichage, POST pour le traitement)
    request_type = request.GET.get("type") or request.POST.get("request_type")
    is_audit_request = request_type == AUDIT_REQUEST_TYPE

    initial_data = {}
    if is_audit_request:
        initial_data["message"] = AUDIT_PREFILL_MESSAGE

    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_obj = form.save()

            # Préparation de l'email
            subject = f"Nouveau contact de {contact_obj.name} - Horus Global"
            if is_audit_request:
                subject = f"🚨 DEMANDE D'AUDIT - {contact_obj.name}"

            message = f"""
Nouveau message reçu depuis le site :

Type : {'Audit' if is_audit_request else 'Contact standard'}
Nom : {contact_obj.name}
Email : {contact_obj.email}
Téléphone : {contact_obj.phone}

Message :
{contact_obj.message}
""".strip()

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.PUBLIC_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                logger.error("Erreur envoi email contact : %s", e, exc_info=True)

            messages.success(
                request,
                f"Merci {contact_obj.name} ! Votre demande a bien été envoyée."
            )
            return redirect("contact")
    else:
        form = ContactForm(initial=initial_data)

    return render(request, "core/contact.html", {
        "form": form,
        "request_type": request_type,
        "is_audit_request": is_audit_request,
    })


def portfolio(request):
    """Page Portfolio avec pagination"""
    projects_list = Project.objects.all().order_id("-id")  # Optionnel: tri par ID
    paginator = Paginator(projects_list, 9)
    page_number = request.GET.get("page")
    projects = paginator.get_page(page_number)

    return render(request, "core/portfolio.html", {"projects": projects})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(request, "core/project_detail.html", {"project": project})