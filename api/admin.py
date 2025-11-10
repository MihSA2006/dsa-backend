# api/admin.py

from django.contrib import admin
from .models import Challenge, TestCase


class TestCaseInline(admin.TabularInline):
    """Affiche les test cases dans la page du challenge"""
    model = TestCase
    extra = 1
    fields = ['order', 'input_file', 'output_file', 'is_sample']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'is_active', 'created_at']
    list_filter = ['difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TestCaseInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'slug', 'difficulty', 'is_active')
        }),
        ('Fichiers', {
            'fields': ('description_file', 'template_file')
        }),
    )


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['challenge', 'order', 'is_sample']
    list_filter = ['challenge', 'is_sample']
    ordering = ['challenge', 'order']