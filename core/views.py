from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import ContactForm
from .models import Article, Project
from django.core.mail import send_mail
from django.conf import settings

def home(request):
    """Page d'accueil"""
    recent_articles = Article.objects.filter(is_published=True)[:3]
    return render(request, 'core/home.html', {
        'recent_articles': recent_articles
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
            # 1. Sauvegarde dans la base de données (Admin)
            contact = form.save()

            # 2. Envoi de l'email de notification à VOUS (Admin)
            subject = f"Nouveau contact de {contact.name} - Horus Global"
            message = f"""
            Nouveau message reçu depuis le site :

            Nom : {contact.name}
            Email : {contact.email}
            Téléphone : {contact.phone}

            Message :
            {contact.message}
            """

            # On envoie l'email
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.PUBLIC_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur d'envoi email: {e}")

            messages.success(request, f"Merci {contact.name} ! Votre message a bien été envoyé.")
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'core/contact.html', {'form': form})
def portfolio(request):
    """Page Portfolio avec tous les projets"""
    projects = Project.objects.all()
    return render(request, 'core/portfolio.html', {'projects': projects})
def project_detail(request, slug):
    project = get_object_or_404(Project, slug=slug)
    return render(request, 'core/project_detail.html', {'project': project})
