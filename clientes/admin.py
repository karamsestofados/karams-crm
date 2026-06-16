from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Cliente, HistoricoInteracao, Produto


class ProdutoResource(resources.ModelResource):
    class Meta:
        model = Produto
        fields = ('id', 'nome', 'categoria', 'novo')


class ClienteResource(resources.ModelResource):
    class Meta:
        model = Cliente
        fields = (
            'id', 'vendedor', 'categoria', 'nome', 'tipo_cliente', 'segmento',
            'origem_lead', 'status_funil', 'regiao_atuacao', 'cidade', 'estado',
            'cep', 'telefone', 'responsavel', 'instagram', 'endereco',
            'data_primeiro_contato', 'feedback_original', 'ativo_no_sistema', 'legacy_id',
        )


class HistoricoInteracaoInline(admin.TabularInline):
    model = HistoricoInteracao
    extra = 0
    fields = ('data', 'tipo', 'vendedor', 'observacao', 'valor')
    autocomplete_fields = ['vendedor']


@admin.register(Produto)
class ProdutoAdmin(ImportExportModelAdmin):
    resource_class = ProdutoResource
    list_display = ('nome', 'categoria', 'novo')
    list_filter = ('novo', 'categoria')
    search_fields = ('nome',)


@admin.register(Cliente)
class ClienteAdmin(ImportExportModelAdmin):
    resource_class = ClienteResource
    list_display = (
        'nome', 'tipo_cliente', 'segmento', 'status_funil', 'categoria',
        'cidade', 'estado', 'vendedor', 'ativo_no_sistema',
    )
    list_filter = (
        'tipo_cliente', 'segmento', 'origem_lead', 'status_funil', 'regiao_atuacao',
        'categoria', 'estado', 'ativo_no_sistema', 'vendedor',
    )
    search_fields = ('nome', 'cidade', 'telefone', 'cep', 'legacy_id')
    filter_horizontal = ('produtos_exclusivos',)
    inlines = [HistoricoInteracaoInline]
    autocomplete_fields = ['vendedor']


@admin.register(HistoricoInteracao)
class HistoricoInteracaoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'tipo', 'data', 'vendedor', 'valor')
    list_filter = ('tipo', 'data', 'vendedor')
    search_fields = ('cliente__nome', 'observacao')
    filter_horizontal = ('produtos',)
    autocomplete_fields = ['cliente', 'vendedor']
