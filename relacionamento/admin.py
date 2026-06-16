from django.contrib import admin
from django.utils import timezone

from .models import AtividadeCliente


@admin.register(AtividadeCliente)
class AtividadeClienteAdmin(admin.ModelAdmin):
    list_display = (
        'cliente', 'tipo_contato', 'resultado', 'usuario', 'data_criacao',
        'proxima_acao', 'data_proxima_acao', 'concluida',
    )
    list_filter = ('tipo_contato', 'resultado', 'concluida', 'proxima_acao')
    search_fields = ('cliente__nome', 'assunto', 'resumo')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'deleted_at', 'deleted_by')
    autocomplete_fields = ['cliente', 'usuario', 'produto_relacionado']
    date_hierarchy = 'data_criacao'

    actions = ['soft_delete_selecionados']

    @admin.action(description='Excluir (soft delete) selecionados')
    def soft_delete_selecionados(self, request, queryset):
        for obj in queryset.filter(deleted_at__isnull=True):
            obj.delete(usuario=request.user)

    def has_delete_permission(self, request, obj=None):
        return False
