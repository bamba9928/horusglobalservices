from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from ckeditor_uploader.fields import RichTextUploadingField


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class Contact(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom complet")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone")
    message = models.TextField(verbose_name="Message")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Date de réception")
    is_read = models.BooleanField(default=False, verbose_name="Lu")
    is_responded = models.BooleanField(default=False, verbose_name="Répondu")

    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} - {self.email}"


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------
class Article(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL (Slug)")
    summary = models.TextField(max_length=500, verbose_name="Résumé pour SEO")
    content = RichTextUploadingField(verbose_name="Contenu")
    image = models.ImageField(upload_to="blog/", blank=True, null=True, verbose_name="Image de couverture")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Date de publication")
    is_published = models.BooleanField(default=True, verbose_name="Publié")

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles de blog"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("article_detail", kwargs={"slug": self.slug})


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------
class Project(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre du projet")
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(verbose_name="Description courte")
    image = models.ImageField(upload_to="portfolio/", verbose_name="Image de présentation")
    url = models.URLField(blank=True, verbose_name="Lien vers le site (Live)")
    github_url = models.URLField(blank=True, verbose_name="Lien GitHub (Optionnel)")
    technologies = models.CharField(
        max_length=200,
        help_text="Séparez par des virgules (ex: Django, Tailwind, Docker)",
    )
    created_at = models.DateField(default=timezone.now, verbose_name="Date de réalisation")
    is_featured = models.BooleanField(default=False, verbose_name="Afficher sur l'accueil ?")

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Portfolio"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_tech_list(self):
        return [tech.strip() for tech in self.technologies.split(",")]

    def get_absolute_url(self):
        return reverse("project_detail", kwargs={"slug": self.slug})


# ---------------------------------------------------------------------------
# CustomUser
# ---------------------------------------------------------------------------
class CustomUserManager(BaseUserManager):
    """Manager pour CustomUser avec email comme identifiant principal."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if not extra_fields.get("is_staff"):
            raise ValueError("Un superuser doit avoir is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Un superuser doit avoir is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Utilisateur personnalisé — identifiant principal : email (pas username).
    Étendre ce modèle pour ajouter des champs métier supplémentaires.
    """

    email = models.EmailField(unique=True, verbose_name="Adresse email")
    first_name = models.CharField(max_length=50, blank=True, verbose_name="Prénom")
    last_name = models.CharField(max_length=50, blank=True, verbose_name="Nom")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="Photo de profil")

    # Rôle / profil métier
    ROLE_CHOICES = [
        ("admin", "Administrateur"),
        ("manager", "Manager"),
        ("client", "Client"),
        ("staff", "Staff"),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="client",
        verbose_name="Rôle",
    )

    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_staff = models.BooleanField(default=False, verbose_name="Accès admin")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Date d'inscription")

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.get_full_name() or self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name or self.email