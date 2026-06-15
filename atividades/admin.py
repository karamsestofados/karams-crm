from django.contrib import admin

from .models import RegistroDiario


@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ('nome_cliente', 'resultado', 'data', 'vendedor', 'valor')
    list_filter = ('resultado', 'data', 'vendedor')
    search_fields = ('cliente__nome', 'cliente_nome_livre', 'observacao')
    autocomplete_fields = ['cliente', 'vendedor']
    date_hierarchy = 'data'
