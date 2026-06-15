from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'papel', 'taxa_comissao_padrao', 'ativo', 'is_staff')
    list_filter = ('papel', 'ativo', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Karams CRM', {
            'fields': ('papel', 'taxa_comissao_padrao', 'ativo', 'avatar', 'tema'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Karams CRM', {
            'fields': ('papel', 'taxa_comissao_padrao', 'ativo', 'tema'),
        }),
    )
