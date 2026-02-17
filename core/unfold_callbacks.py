from django.apps import apps
from django.db.utils import OperationalError, ProgrammingError


def _safe_count(qs) -> int:
    try:
        return qs.count()
    except (OperationalError, ProgrammingError):
        return 0


def dashboard_callback(request, context):
    Contact = apps.get_model("core", "Contact")
    Article = apps.get_model("core", "Article")

    context["kpi_unread_contacts"] = _safe_count(Contact.objects.filter(is_read=False))
    context["kpi_published_articles"] = _safe_count(Article.objects.filter(is_published=True))
    return context


def unread_contacts_badge(request) -> int:
    Contact = apps.get_model("core", "Contact")
    return _safe_count(Contact.objects.filter(is_read=False))
