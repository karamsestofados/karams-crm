from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import (
    Cliente,
    ClienteProduto,
    HistoricoInteracao,
    Produto,
    ProdutoExclusividade,
)


class ProdutoResource(resources.ModelResource):
    class Meta:
        model = Produto
        fields = ('id', 'nome', 'descricao', 'categoria', 'tipo_produto', 'ativo')


class ClienteResource(resources.ModelResource):
    class Meta:
        model = Cliente
        fields = (
            'id', 'vendedor', 'categoria', 'nome', 'tipo_cliente', 'modalidade_cliente', 'segmento',
            'origem_lead', 'status_funil', 'regiao_atuacao', 'cidade', 'estado',
            'cep', 'telefone', 'responsavel', 'instagram', 'endereco',
            'data_primeiro_contato', 'feedback_original', 'legacy_id',
        )


class ClienteProdutoInline(admin.TabularInline):
    model = ClienteProduto
    extra = 0
    fields = ('produto', 'data_inicio', 'observacoes')
    autocomplete_fields = ['produto']


class HistoricoInteracaoInline(admin.TabularInline):
    model = HistoricoInteracao
    extra = 0
    fields = ('data', 'tipo', 'vendedor', 'observacao', 'valor')
    autocomplete_fields = ['vendedor']
    readonly_fields = ('data', 'tipo', 'vendedor', 'observacao', 'valor')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ProdutoExclusividadeInline(admin.TabularInline):
    model = ProdutoExclusividade
    extra = 0
    fields = ('regiao', 'data_inicio', 'data_fim', 'observacoes')


@admin.register(Produto)
class ProdutoAdmin(ImportExportModelAdmin):
    resource_class = ProdutoResource
    list_display = ('nome', 'tipo_produto', 'categoria', 'ativo', 'data_criacao')
    list_filter = ('tipo_produto', 'ativo', 'categoria')
    search_fields = ('nome', 'descricao', 'categoria')
    inlines = [ProdutoExclusividadeInline]


@admin.register(ClienteProduto)
class ClienteProdutoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'produto', 'data_inicio')
    list_filter = ('produto__tipo_produto', 'data_inicio')
    search_fields = ('cliente__nome', 'produto__nome')
    autocomplete_fields = ['cliente', 'produto']


@admin.register(Cliente)
class ClienteAdmin(ImportExportModelAdmin):
    resource_class = ClienteResource
    list_display = (
        'nome', 'tipo_cliente', 'modalidade_cliente', 'segmento', 'status_funil', 'categoria',
        'cidade', 'estado', 'vendedor',
    )
    list_filter = (
        'tipo_cliente', 'modalidade_cliente', 'segmento', 'origem_lead', 'status_funil', 'regiao_atuacao',
        'categoria', 'estado', 'vendedor',
    )
    search_fields = ('nome', 'cidade', 'telefone', 'cep', 'legacy_id')
    inlines = [ClienteProdutoInline, HistoricoInteracaoInline]
    autocomplete_fields = ['vendedor']


@admin.register(HistoricoInteracao)
class HistoricoInteracaoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'tipo', 'data', 'vendedor', 'valor')
    list_filter = ('tipo', 'data', 'vendedor')
    search_fields = ('cliente__nome', 'observacao')
    filter_horizontal = ('produtos',)
    autocomplete_fields = ['cliente', 'vendedor']
    readonly_fields = ('cliente', 'tipo', 'data', 'vendedor', 'observacao', 'valor', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProdutoExclusividade)
class ProdutoExclusividadeAdmin(admin.ModelAdmin):
    list_display = ('produto', 'regiao', 'data_inicio', 'data_fim')
    list_filter = ('regiao',)
    search_fields = ('produto__nome',)
    autocomplete_fields = ['produto']
