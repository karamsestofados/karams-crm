from django.contrib import admin

from .models import ConquistaVendedor, MetaMensal, Venda


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
    list_display = (
        'vendedor', 'mes', 'ano', 'meta_contatos', 'meta_clientes_novos',
        'meta_propostas', 'meta_visitas', 'meta_vendas', 'ativo',
    )
    list_filter = ('ano', 'mes', 'vendedor', 'ativo')
    autocomplete_fields = ['vendedor']


@admin.register(ConquistaVendedor)
class ConquistaVendedorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'mes', 'ano', 'data_conquista')
    list_filter = ('tipo', 'ano', 'mes')
