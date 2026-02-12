import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Charger le .env AVANT toute lecture de variable
load_dotenv(BASE_DIR / ".env")

# 2. Environnement
ENV = os.getenv("ENV", "dev")
DEBUG = os.getenv("DEBUG", "False") == "True"

# 3. SECRET_KEY — obligatoire, pas de fallback silencieux en prod
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # Valeur de dev uniquement — jamais utilisée en prod
        SECRET_KEY = "dev-insecure-fallback-key-change-in-production"
    else:
        raise ValueError(
            "DJANGO_SECRET_KEY est manquante dans l'environnement. "
            "Définissez-la dans le fichier .env avant de lancer en production."
        )

# 4. Modèle utilisateur personnalisé
AUTH_USER_MODEL = "core.CustomUser"

ALLOWED_HOSTS = ["horuservices.cloud", "www.horuservices.cloud", "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = ["https://horuservices.cloud", "https://www.horuservices.cloud"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "ckeditor",
    "ckeditor_uploader",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------
# En développement : SQLite (rapide à démarrer)
# En production    : PostgreSQL (requis pour multi-workers Gunicorn / pgbouncer)
#
# Variables .env attendues en prod :
#   DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# ---------------------------------------------------------------------------
if DEBUG:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
            "NAME": os.getenv("DB_NAME", "horuservices"),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,  # Connexions persistantes (optimisation prod)
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"  # UTC+0 sans changement d'heure (équivalent UTC mais explicite)
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Clé primaire par défaut
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Fichiers statiques & médias
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []

STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    STATICFILES_DIRS.append(STATIC_DIR)

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = "no-reply@horuservices.cloud"
PUBLIC_EMAIL = os.getenv("PUBLIC_EMAIL", "bambadisala@gmail.com")

# ---------------------------------------------------------------------------
# URLs de contact centralisées
# ---------------------------------------------------------------------------
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/221773409658")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "debug.log",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}

# ---------------------------------------------------------------------------
# CKEditor
# ---------------------------------------------------------------------------
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"

CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "height": 400,
        "width": "100%",
        "toolbar_Custom": [
            ["Bold", "Italic", "Underline"],
            ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote"],
            ["Link", "Unlink"],
            ["RemoveFormat", "Source"],
            ["Image", "Table", "HorizontalRule"],
            ["Format", "Styles"],
            ["Maximize"],
        ],
        "uiColor": "#E0E0E0",
    }
}

# ---------------------------------------------------------------------------
# Sites framework
# ---------------------------------------------------------------------------
SITE_ID = 1