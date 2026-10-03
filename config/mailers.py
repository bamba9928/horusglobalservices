"""Configuration MAILERS (Django 6.1).

Remplace EMAIL_BACKEND / EMAIL_HOST / EMAIL_PORT / EMAIL_USE_TLS / EMAIL_HOST_USER /
EMAIL_HOST_PASSWORD / EMAIL_TIMEOUT, depreciés en 6.1 et retirés avant Django 7.0.
Les variables d'environnement restent les memes : le .env du serveur n'a pas a changer.
Fonction pure (environnement passé en argument) pour pouvoir la tester sans rien envoyer.
"""
import os

TRUE_VALUES = ("1", "true", "yes", "on")


def build_mailers(debug, environ=os.environ):
    if debug:
        # Developpement : les mails s'affichent dans la console.
        return {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

    return {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": environ.get("EMAIL_HOST", "smtp.sendgrid.net"),
                "port": int(environ.get("EMAIL_PORT", "587")),
                "use_tls": environ.get("EMAIL_USE_TLS", "True").strip().lower() in TRUE_VALUES,
                "username": environ.get("EMAIL_HOST_USER", ""),
                "password": environ.get("EMAIL_HOST_PASSWORD", ""),
                "timeout": int(environ.get("EMAIL_TIMEOUT", "20")),
            },
        }
    }
