from django.contrib import admin

from .models import BackupLog


@admin.register(BackupLog)
class BackupLogAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'data_hora', 'usuario', 'arquivo')
    list_filter = ('tipo', 'data_hora')
    readonly_fields = ('data_hora',)
