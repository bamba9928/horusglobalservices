from django.contrib import admin
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Administration des messages de contact"""

    list_display = ['name', 'email', 'phone', 'created_at', 'is_read', 'is_responded']
    list_filter = ['is_read', 'is_responded', 'created_at']
    search_fields = ['name', 'email', 'phone', 'message']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informations contact', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Statut', {
            'fields': ('is_read', 'is_responded', 'created_at')
        }),
    )

    actions = ['mark_as_read', 'mark_as_responded']

    def mark_as_read(self, request, queryset):
        """Marquer comme lu"""
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} message(s) marqué(s) comme lu(s).")

    mark_as_read.short_description = "Marquer comme lu"

    def mark_as_responded(self, request, queryset):
        """Marquer comme répondu"""
        updated = queryset.update(is_responded=True, is_read=True)
        self.message_user(request, f"{updated} message(s) marqué(s) comme répondu(s).")

    mark_as_responded.short_description = "Marquer comme répondu"