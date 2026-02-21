# ------------------------------------------------------------
# Mouhamadou Bamba Dieng 2026
# ------------------------------------------------------------
import os
from pathlib import Path

from dotenv import load_dotenv
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

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
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    # Rich text
    "ckeditor",
    "ckeditor_uploader",
    # Project
    "core",
    "django_resized",
]

# ------------------------------------------------------------
# Middleware
# ------------------------------------------------------------
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
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ------------------------------------------------------------
# Email
# ------------------------------------------------------------
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend"
)

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
EMAIL_PORT = env_int("EMAIL_PORT", "587")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", "True")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@horuservices.cloud")
PUBLIC_EMAIL = os.getenv("PUBLIC_EMAIL", "bambadisala@gmail.com")

# ------------------------------------------------------------
# URLs de contact
# ------------------------------------------------------------
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/221773409658")
GITHUB_URL = os.getenv("GITHUB_URL", "https://github.com/bamba9928")
LINKEDIN_URL = os.getenv("LINKEDIN_URL", "https://www.linkedin.com/in/horusglobalservices/")
FACEBOOK_URL = os.getenv("FACEBOOK_URL", "https://www.facebook.com/dieng.sala.47647")
X_URL = os.getenv("X_URL", "https://x.com/horuservices")

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
        "file": {
            "level": "ERROR",
            "class": "logging.FileHandler",
            "filename": str(LOG_DIR / "app-error.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"] if DEBUG else ["file"],
            "level": "INFO" if DEBUG else "ERROR",
            "propagate": True,
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
# CKEditor (sans duplication)
# ------------------------------------------------------------
CKEDITOR_UPLOAD_PATH = os.getenv("CKEDITOR_UPLOAD_PATH", "uploads/")
CKEDITOR_IMAGE_BACKEND = os.getenv("CKEDITOR_IMAGE_BACKEND", "pillow")
CKEDITOR_ALLOW_NONIMAGE_FILES = env_bool("CKEDITOR_ALLOW_NONIMAGE_FILES", "False")

FILE_UPLOAD_MAX_MEMORY_SIZE = env_int("FILE_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024))
DATA_UPLOAD_MAX_MEMORY_SIZE = env_int("DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024))

CKEDITOR_CONFIGS = {
    "default": {
        "toolbar": "Custom",
        "height": 400,
        "width": "100%",
        "uiColor": "#F3F4F6",
        "language": "fr",
        "toolbarCanCollapse": True,
        "removePlugins": "elementspath",
        "extraPlugins": ",".join(
            [
                "autolink",
                "justify",
                "pastetext",
                "pastefromword",
                "image2",
                "uploadimage",
                "table",
                "tabletools",
            ]
        ),
        "filebrowserBrowseUrl": "/ckeditor/browse/",
        "filebrowserUploadUrl": "/ckeditor/upload/",
        "imageUploadUrl": "/ckeditor/upload/",
        "linkDefaultProtocol": "https://",
        "linkShowAdvancedTab": False,
        "linkShowTargetTab": True,
        "toolbar_Custom": [
            ["Maximize", "Source"],
            ["Format", "Styles"],
            ["Bold", "Italic", "Underline", "-", "RemoveFormat"],
            ["JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"],
            ["NumberedList", "BulletedList", "-", "Outdent", "Indent", "-", "Blockquote"],
            ["Link", "Unlink"],
            ["Image", "Table", "HorizontalRule"],
        ],
    }
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
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "20"))
