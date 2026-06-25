from django.contrib import admin

from .models import ExtensionApiToken


@admin.register(ExtensionApiToken)
class ExtensionApiTokenAdmin(admin.ModelAdmin):
    list_display = ('prefixo', 'usuario', 'ativo', 'criado_em', 'ultimo_uso')
    list_filter = ('ativo',)
    search_fields = ('prefixo', 'usuario__username', 'usuario__first_name')
    readonly_fields = ('token_hash', 'prefixo', 'criado_em', 'ultimo_uso')
