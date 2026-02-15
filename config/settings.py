# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Charger .env
load_dotenv(BASE_DIR / ".env")

# ------------------------------------------------------------
# ENV / DEBUG
# ------------------------------------------------------------
ENV = os.getenv("ENV", "dev").lower()  # dev | prod
DEBUG = os.getenv("DEBUG", "False").strip().lower() in ("1", "true", "yes", "on")
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
def _csv(name: str, default: str = ""):
    raw = os.getenv(name, default).strip()
    return [x.strip() for x in raw.split(",") if x.strip()]

ALLOWED_HOSTS = _csv(
    "ALLOWED_HOSTS",
    default="127.0.0.1,localhost,horuservices.cloud,www.horuservices.cloud",
)

CSRF_TRUSTED_ORIGINS = _csv(
    "CSRF_TRUSTED_ORIGINS",
    default="https://horuservices.cloud,https://www.horuservices.cloud",
)

# ------------------------------------------------------------
# Apps
# ------------------------------------------------------------
AUTH_USER_MODEL = "core.CustomUser"

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

ROOT_URLCONF = "config.urls"

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
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ------------------------------------------------------------
# Database
# - Dev: SQLite par défaut (simple)
# - Prod: PostgreSQL
# - Tu peux forcer Postgres en dev en mettant DB_ENGINE=django.db.backends.postgresql
# ------------------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "").strip()

if (not DB_ENGINE and not IS_PROD) or (DB_ENGINE == "django.db.backends.sqlite3"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE or "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "horuservices"),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        }
    }

# ------------------------------------------------------------
# Password validation
# ------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------
# i18n
# ------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------
# Static / Media
# ------------------------------------------------------------
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = []
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    STATICFILES_DIRS.append(STATIC_DIR)

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_ROOT = BASE_DIR / "media"

# ------------------------------------------------------------
# Email
# ------------------------------------------------------------
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.sendgrid.net")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip().lower() in ("1", "true", "yes", "on")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@horuservices.cloud")
PUBLIC_EMAIL = os.getenv("PUBLIC_EMAIL", "bambadisala@gmail.com")

# ------------------------------------------------------------
# URLs de contact
# ------------------------------------------------------------
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/221773409658")
GITHUB_URL = os.getenv("GITHUB_URL", "https://github.com/bamba9928")
LINKEDIN_URL = os.getenv("LINKEDIN_URL", "https://linkedin.com/in/...")
FACEBOOK_URL = os.getenv("FACEBOOK_URL", "https://facebook.com/...")
X_URL = os.getenv("X_URL", "https://x.com/...")

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
# Security (prod only)
# ------------------------------------------------------------
if IS_PROD:
    # Si derrière proxy (Nginx/Cloudflare/Load balancer)
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

    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ------------------------------------------------------------
# CKEditor
# ------------------------------------------------------------
CKEDITOR_UPLOAD_PATH = os.getenv("CKEDITOR_UPLOAD_PATH", "uploads/")
CKEDITOR_IMAGE_BACKEND = os.getenv("CKEDITOR_IMAGE_BACKEND", "pillow")

# Recommandé: limiter aux images
CKEDITOR_ALLOW_NONIMAGE_FILES = os.getenv("CKEDITOR_ALLOW_NONIMAGE_FILES", "False").strip().lower() in ("1", "true", "yes", "on")

# Limites upload (optionnel)
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(5 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024)))

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
CKEDITOR_ALLOW_NONIMAGE_FILES = False
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024       # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024      # 10 MB

# ------------------------------------------------------------
# Sites framework
# ------------------------------------------------------------
SITE_ID = int(os.getenv("SITE_ID", "1"))
