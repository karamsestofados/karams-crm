from django.contrib import admin

from .models import AlertaRetorno, NotaRelacionamento


@admin.register(NotaRelacionamento)
class NotaRelacionamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'data', 'texto_resumo')
    list_filter = ('data',)
    search_fields = ('cliente__nome', 'texto')
    autocomplete_fields = ['cliente']
    date_hierarchy = 'data'

    @admin.display(description='Texto')
    def texto_resumo(self, obj):
        return obj.texto[:60] + '…' if len(obj.texto) > 60 else obj.texto


@admin.register(AlertaRetorno)
class AlertaRetornoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'vendedor', 'data_contato', 'data_alerta', 'dispensado')
    list_filter = ('dispensado', 'data_alerta', 'vendedor')
    search_fields = ('cliente__nome',)
    autocomplete_fields = ['cliente', 'vendedor']
    readonly_fields = ('cliente', 'vendedor', 'data_contato', 'data_alerta', 'dispensado')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
