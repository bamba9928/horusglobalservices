# ------------------------------------------------------------
# Mouhamadou Bamba Dieng 2026
# ------------------------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _ 

from .mailers import build_mailers

# ------------------------------------------------------------
# Base / .env
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def env_bool(name: str, default: str = "False") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def env_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


def env_csv(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default).strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


# ------------------------------------------------------------
# ENV / DEBUG
# ------------------------------------------------------------
ENV = os.getenv("ENV", "dev").lower()  # dev | prod
DEBUG = env_bool("DEBUG", "False")
IS_PROD = (ENV == "prod") and (not DEBUG)

# ------------------------------------------------------------
# SECRET KEY
# ------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-insecure-fallback-key-change-in-production"
    else:
        raise ValueError("DJANGO_SECRET_KEY manquante en production.")

# ------------------------------------------------------------
# Hosts / CSRF
# ------------------------------------------------------------
ALLOWED_HOSTS = env_csv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,horuservices.cloud,www.horuservices.cloud",
)

CSRF_TRUSTED_ORIGINS = env_csv(
    "CSRF_TRUSTED_ORIGINS",
    "https://horuservices.cloud,https://www.horuservices.cloud",
)

# ------------------------------------------------------------
# Core Django
# ------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------
# Apps
# ------------------------------------------------------------
INSTALLED_APPS = [
    # Admin UI
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "config.apps.ProjectStaticFilesConfig",  # = django.contrib.staticfiles, sans les sources Tailwind
    "django.contrib.sites",
    "django.contrib.sitemaps",
    # Rich text
    "django_ckeditor_5",
    # Project
    "core",
    "django_resized",
]

# ------------------------------------------------------------
# Middleware
# ------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.ContentSecurityPolicyMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ------------------------------------------------------------
# Templates
# ------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.global_settings",
                "core.context_processors.csp_nonce",
            ],
        },
    }
]
# ------------------------------------------------------------
# Database
# - Dev: SQLite par défaut (si DB_ENGINE vide)
# - Prod: PostgreSQL (ou forcer via DB_ENGINE)
# - Check prod: refuse si credentials DB manquants
# ------------------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "").strip()

USE_SQLITE = (
    (not DB_ENGINE and not IS_PROD)
    or DB_ENGINE == "django.db.backends.sqlite3"
)

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DB_NAME = os.getenv("DB_NAME", "horuservices")
    DB_USER = os.getenv("DB_USER", "").strip()
    DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
    DB_HOST = os.getenv("DB_HOST", "localhost").strip()
    DB_PORT = os.getenv("DB_PORT", "5432").strip()

    # Check "prod" : credentials obligatoires
    if IS_PROD:
        missing = []
        if not DB_USER:
            missing.append("DB_USER")
        if not DB_PASSWORD:
            missing.append("DB_PASSWORD")
        if not DB_HOST:
            missing.append("DB_HOST")
        if not DB_NAME:
            missing.append("DB_NAME")

        if missing:
            raise ValueError(
                "Configuration DB incomplète en production (ENV=prod, DEBUG=False). "
                f"Variables manquantes/vides: {', '.join(missing)}"
            )

    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE or "django.db.backends.postgresql",
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }

# ------------------------------------------------------------
# Auth / Sites
# ------------------------------------------------------------
AUTH_USER_MODEL = "core.CustomUser"
SITE_ID = env_int("SITE_ID", "1")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------
# Static / Media
# ------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
# Fichiers statiques VERSIONNES en production (app.8f3c2a1b.js au lieu de app.js).
# nginx et Cloudflare servent /static/ en cache "immutable" 30 jours : sans empreinte dans
# le nom, un changement de version (Unfold, Django, CKEditor...) laisse le HTML neuf charger
# d'anciens CSS/JS gardes en cache -> admin casse apres la montee d'Unfold 0.80 -> 0.108
# ("adminTheme is not defined"...). Avec l'empreinte, chaque nouveau contenu a une nouvelle URL.
# L'ancien reglage STATICFILES_STORAGE n'existe plus depuis Django 5.1 : il etait ignore,
# les noms n'ont donc jamais ete versionnes. Hors production (DEBUG) : stockage simple, sans
# manifeste, pour que le serveur de dev et les tests fonctionnent sans collectstatic.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
# Fichier absent du manifeste : hache a la volee depuis le disque plutot que lever une erreur.
WHITENOISE_MANIFEST_STRICT = False

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ------------------------------------------------------------
# Email
# ------------------------------------------------------------
# Django 6.1 : MAILERS remplace EMAIL_BACKEND/EMAIL_HOST/... (voir config/mailers.py).
# Memes variables d'environnement qu'avant : EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS,
# EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_TIMEOUT.
MAILERS = build_mailers(DEBUG)

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@horuservices.cloud")
PUBLIC_EMAIL = os.getenv("PUBLIC_EMAIL", "contact@horus-assur.digital")

# ------------------------------------------------------------
# URLs de contact
# ------------------------------------------------------------
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/221773409658")
GITHUB_URL = os.getenv("GITHUB_URL", "https://github.com/bamba9928")
LINKEDIN_URL = os.getenv("LINKEDIN_URL", "https://www.linkedin.com/in/horusglobalservices/")
FACEBOOK_URL = os.getenv("FACEBOOK_URL", "https://www.facebook.com/share/1EXSwjQNYy/")
X_URL = os.getenv("X_URL", "https://x.com/horuservices")

# ------------------------------------------------------------
# Google Analytics 4
# ------------------------------------------------------------
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "G-2875RWT67C")

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {"format": "[{levelname}] {message}", "style": "{"},
    },
    "handlers": {
        "console": {"level": "DEBUG", "class": "logging.StreamHandler", "formatter": "simple"},
        # Rotation : l'ancien FileHandler laissait app-error.log grossir sans limite
        # (34 Mo, dont ~62 000 lignes de bruit DisallowedHost).
        "file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app-error.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "verbose",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"] if DEBUG else ["file"],
            "level": "INFO" if DEBUG else "ERROR",
            "propagate": True,
        },
        # Bots qui scannent le site par IP / avec un Host inconnu : Django les
        # rejette deja en 400. Les logguer en ERROR noie les vraies erreurs.
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "propagate": False,
        },
    },
}

# ------------------------------------------------------------
# Security (prod only) — config (sans débats)
# ------------------------------------------------------------
if IS_PROD:
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"

    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", "31536000")
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ------------------------------------------------------------
# Uploads / limites de requete
# ------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024))

# ------------------------------------------------------------
# CKEditor 5 (django-ckeditor-5) — editeur riche de l'admin
# Remplace CKEditor 4 (fin de vie, failles XSS connues). Le paquet fixe
# licenseKey='GPL' : CKEditor 5 est utilise sous licence GPL (voir ckeditor.com/legal).
# ------------------------------------------------------------
CKEDITOR_5_FILE_STORAGE = "core.storage.CKEditorUploadStorage"  # media/uploads/AAAA/MM/
CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "jpg", "png", "gif", "webp"]
CKEDITOR_5_MAX_FILE_SIZE = 5  # Mo
CKEDITOR_5_FILE_UPLOAD_PERMISSION = "staff"  # seuls les comptes staff peuvent envoyer des images
CKEDITOR_5_CUSTOM_CSS = "css/ckeditor-admin.v1.css"  # theme sombre (classe "dark" d'Unfold)

# Titres h1 a h4 autorises : les articles existants contiennent des <h1> (30) qu'il faut
# conserver tels quels lors d'une reedition.
CKEDITOR_5_CONFIGS = {
    "default": {
        "language": "fr",
        "toolbar": {
            "items": [
                "sourceEditing", "|",
                "heading", "|",
                "bold", "italic", "underline", "code", "removeFormat", "|",
                "alignment", "|",
                "bulletedList", "numberedList", "outdent", "indent", "|",
                "blockQuote", "codeBlock", "|",
                "link", "insertImage", "insertTable", "horizontalLine", "|",
                "undo", "redo",
            ],
            "shouldNotGroupWhenFull": True,
        },
        "heading": {
            "options": [
                {"model": "paragraph", "title": "Paragraphe", "class": "ck-heading_paragraph"},
                {"model": "heading1", "view": "h1", "title": "Titre 1", "class": "ck-heading_heading1"},
                {"model": "heading2", "view": "h2", "title": "Titre 2", "class": "ck-heading_heading2"},
                {"model": "heading3", "view": "h3", "title": "Titre 3", "class": "ck-heading_heading3"},
                {"model": "heading4", "view": "h4", "title": "Titre 4", "class": "ck-heading_heading4"},
            ]
        },
        "codeBlock": {
            "languages": [
                {"language": "plaintext", "label": "Texte brut"},
                {"language": "bash", "label": "Bash / Shell"},
                {"language": "python", "label": "Python"},
                {"language": "javascript", "label": "JavaScript"},
                {"language": "typescript", "label": "TypeScript"},
                {"language": "html", "label": "HTML"},
                {"language": "css", "label": "CSS"},
                {"language": "json", "label": "JSON"},
                {"language": "yaml", "label": "YAML"},
                {"language": "sql", "label": "SQL"},
                {"language": "dockerfile", "label": "Dockerfile"},
                {"language": "rust", "label": "Rust"},
                {"language": "go", "label": "Go"},
                {"language": "nginx", "label": "Nginx"},
            ]
        },
        "link": {
            "defaultProtocol": "https://",
            "addTargetToExternalLinks": True,
        },
        "list": {"properties": {"styles": True, "startIndex": True, "reversed": True}},
        "image": {
            "toolbar": [
                "imageTextAlternative", "toggleImageCaption", "|",
                "imageStyle:alignLeft", "imageStyle:alignCenter", "imageStyle:alignRight", "|",
                "resizeImage",
            ],
            "styles": ["alignLeft", "alignCenter", "alignRight"],
        },
        "table": {
            "contentToolbar": [
                "tableColumn", "tableRow", "mergeTableCells", "tableProperties", "tableCellProperties",
            ]
        },
    }
}

# ------------------------------------------------------------
# Content-Security-Policy (site public) — voir core/middleware.py
# ------------------------------------------------------------
CSP_ENABLED = env_bool("CSP_ENABLED", "True")  # interrupteur d'urgence : CSP_ENABLED=False dans .env
CSP_REPORT_ONLY = env_bool("CSP_REPORT_ONLY", "False")  # True : signale sans bloquer (essais)
CSP_EXCLUDED_PATH_PREFIXES = ("/admin-horus/", "/ckeditor5/")  # admin : Alpine.js exige 'unsafe-eval'

# {nonce} est remplace a chaque requete.
#
# Seul tiers autorise : Google Analytics 4 (gtag.js). Liste MINIMALE verifiee dans un navigateur
# (une mesure part, 0 violation) ; la liste officielle de Google est plus large car elle couvre
# aussi les fonctions publicitaires (Google Ads, Signals), non utilisees ici. img-src autorise
# deja https: (pixel de repli). Le chargement de GA reste soumis au consentement : voir le
# bandeau cookies de base.html, qui ne charge rien tant que l'utilisateur n'a pas clique Accepter.
# La CSP de nginx (static) doit autoriser les memes hotes, sinon GA reste bloque : les deux
# politiques s'additionnent (voir le fichier nginx du depot).
# Cloudflare Web Analytics : la balise est injectee par Cloudflare (pas par nos templates), sans
# cookie ni stockage local, et Cloudflare lui recopie le nonce de cette politique : le script
# passe donc deja ici sans hote en script-src. Il manque seulement l'envoi des mesures
# (connect-src). Cote nginx, la politique statique n'a pas de nonce : il lui faut aussi
# https://static.cloudflareinsights.com en script-src (voir le fichier nginx du depot).
# style-src-attr 'unsafe-inline' : les attributs style="..." des templates (delais
# d'animation, variables CSS) ; sans risque d'execution de script.
CSP_GOOGLE_ANALYTICS_SCRIPT_SRC = ["https://www.googletagmanager.com"]
CSP_GOOGLE_ANALYTICS_CONNECT_SRC = [
    "https://*.google-analytics.com",
    "https://*.analytics.google.com",
    "https://*.googletagmanager.com",
]
CSP_CLOUDFLARE_ANALYTICS_SCRIPT_SRC = ["https://static.cloudflareinsights.com"]  # nginx seulement
CSP_CLOUDFLARE_ANALYTICS_CONNECT_SRC = ["https://cloudflareinsights.com"]
CSP_DIRECTIVES = {
    "default-src": ["'self'"],
    "script-src": ["'self'", "'nonce-{nonce}'", *CSP_GOOGLE_ANALYTICS_SCRIPT_SRC],
    "style-src": ["'self'", "'nonce-{nonce}'"],
    "style-src-attr": ["'unsafe-inline'"],
    "img-src": ["'self'", "data:", "https:"],
    "font-src": ["'self'"],
    "connect-src": ["'self'", *CSP_GOOGLE_ANALYTICS_CONNECT_SRC, *CSP_CLOUDFLARE_ANALYTICS_CONNECT_SRC],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
}
# Page 500 autonome (templates/500.html) : <style> en ligne, rien d'autre.
CSP_SERVER_ERROR_DIRECTIVES = {
    "default-src": ["'none'"],
    "style-src": ["'unsafe-inline'"],
    "base-uri": ["'none'"],
    "form-action": ["'none'"],
    "frame-ancestors": ["'none'"],
}

# ------------------------------------------------------------
# Unfold (inchangé, juste ré-indenté proprement)
# ------------------------------------------------------------
UNFOLD = {
    "SITE_TITLE": "Horus Global Admin",
    "SITE_HEADER": "Horus Global Service",
    "SITE_SYMBOL": "speed",
    "COLORS": {
        "primary": {
            "50": "236, 253, 245",
            "100": "209, 250, 229",
            "200": "167, 243, 208",
            "300": "110, 231, 183",
            "400": "52, 211, 153",
            "500": "16, 185, 129",
            "600": "5, 150, 105",
            "700": "4, 120, 87",
            "800": "6, 95, 70",
            "900": "4, 63, 48",
            "950": "2, 44, 34",
        }
    },
    "DASHBOARD_CALLBACK": "core.unfold_callbacks.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "items": [
                    {
                        "title": _("Vue d'ensemble"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                        "badge": "core.unfold_callbacks.unread_contacts_badge",
                        "badge_variant": "warning",
                        "badge_style": "solid",
                    }
                ],
            }
        ],
    },
}
# ------------------------------------------------------------
# Cache (rate limiting anti-spam)
# FileBasedCache fonctionne avec Gunicorn multi-workers
# ------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(BASE_DIR / "cache"),
        "TIMEOUT": 3600,
    }
}

