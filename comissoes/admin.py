from django.contrib import admin

from .models import MetaMensal, Venda


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'vendedor', 'data', 'valor', 'produtos_texto')
    list_filter = ('data', 'vendedor')
    search_fields = ('cliente__nome', 'produtos_texto')
    autocomplete_fields = ['cliente', 'vendedor']
    filter_horizontal = ('produtos',)
    date_hierarchy = 'data'


@admin.register(MetaMensal)
class MetaMensalAdmin(admin.ModelAdmin):
    list_display = ('vendedor', 'mes', 'ano', 'meta_contatos', 'meta_vendas', 'meta_semanal_contatos')
    list_filter = ('ano', 'mes', 'vendedor')
    autocomplete_fields = ['vendedor']
