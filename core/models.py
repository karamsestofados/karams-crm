from django.db import models


class TipoBackup(models.TextChoices):
    BACKUP = 'backup', 'Backup'
    RESTORE = 'restore', 'Restauração'


class BackupLog(models.Model):
    usuario = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='backups',
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=TipoBackup.choices)
    arquivo = models.FileField(upload_to='backups/', blank=True)
    observacao = models.TextField(blank=True)

    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'log de backup'
        verbose_name_plural = 'logs de backup'

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.data_hora:%d/%m/%Y %H:%M}'
