import logging

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from .models import LegalPage, Article, Project
from .forms import ContactForm

# Configuration du logger
logger = logging.getLogger(__name__)

AUDIT_REQUEST_TYPE = "audit"
AUDIT_PREFILL_MESSAGE = (
    "Bonjour, je souhaiterais obtenir un audit complet "
    "(performance, SQL, sécurité) pour mon projet."
)


def home(request):
    """Page d'accueil optimisée"""
    # On limite les requêtes SQL pour accélérer le FCP
    recent_articles = Article.objects.filter(is_published=True).order_by("-created_at")[:3]
    featured_projects = Project.objects.filter(is_featured=True).order_by("-id")[:3]

    return render(request, "core/home.html", {
        "recent_articles": recent_articles,
        "featured_projects": featured_projects,
    })


def services(request):
    return render(request, "core/services.html")


def skills(request):
    return render(request, "core/skills.html")


def blog(request):
    """Liste des articles"""
    articles = Article.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "core/blog.html", {"articles": articles})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, "core/article_detail.html", {"article": article})


def contact(request):
    """Gestion du formulaire de contact et demande d'audit"""
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
    """Page Portfolio avec pagination et correction order_by"""
    # Correction de l'erreur 500 : order_by au lieu de order_id
    projects_list = Project.objects.all().order_by("-id")

    # Pagination : 9 projets par page
    paginator = Paginator(projects_list, 9)
    page_number = request.GET.get("page")
    projects = paginator.get_page(page_number)

    return render(request, "core/portfolio.html", {"projects": projects})


def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(request, "core/project_detail.html", {"project": project})


def legal_page_detail(request, slug):
    page = get_object_or_404(LegalPage, slug=slug)
    return render(request, 'core/legal.html', {'page': page})


def custom_bad_request_view(request, exception):
    """Vue 404 personnalisée"""
    return render(request, '404.html', status=404)
def robots_txt(request):
    content = render_to_string("robots.txt", {
        "domain": request.get_host(),
        "scheme": "https" if request.is_secure() else "http",
    })
    return HttpResponse(content, content_type="text/plain")