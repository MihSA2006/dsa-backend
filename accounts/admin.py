from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, RegistrationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'nom', 'prenom', 'parcours', 'is_staff']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('nom', 'prenom', 'photo', 'numero_inscription', 'parcours', 'classe')
        }),
    )


@admin.register(RegistrationToken)
class RegistrationTokenAdmin(admin.ModelAdmin):
    list_display = ['email', 'token', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['email']