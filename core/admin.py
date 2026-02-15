from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .models import Contact, Article, Project

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'created_at', 'is_read', 'is_responded']
    list_filter = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'message']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'is_published']
    list_filter = ['is_published', 'created_at']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at', 'is_featured']
    search_fields = ['title', 'technologies']
    prepopulated_fields = {'slug': ('title',)}
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Rôle & Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('date_joined',)}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role')}),
    )