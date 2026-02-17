from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

from .models import CustomUser, Contact, Article, Project


@admin.register(Contact)
class ContactAdmin(ModelAdmin):
    icon = "mail"
    list_display = ("name", "email", "phone", "created_at", "is_read", "is_responded")
    list_filter = ("is_read", "is_responded", "created_at")
    search_fields = ("name", "email", "phone", "message")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)

    actions = ("mark_as_read", "mark_as_responded")

    @admin.action(description="Marquer comme lu")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Marquer comme répondu")
    def mark_as_responded(self, request, queryset):
        queryset.update(is_responded=True)


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    icon = "description"
    list_display = ("title", "category", "created_at", "is_published")
    list_filter = ("category", "is_published", "created_at")
    search_fields = ("title", "summary", "content")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)
    date_hierarchy = "created_at"


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    icon = "rocket_launch"
    list_display = ("title", "created_at", "is_featured")
    list_filter = ("is_featured", "created_at")
    search_fields = ("title", "technologies", "description")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    icon = "person"
    model = CustomUser

    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff", "is_superuser")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Rôle & Permissions", {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "first_name", "last_name", "phone", "role", "password1", "password2")}),
    )
