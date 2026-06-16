from django.conf import settings
from django.db import models

from core.audit import get_current_user


class AuditMixin(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        user = get_current_user()
        if user and user.is_authenticated:
            if not self.pk and not self.created_by_id:
                self.created_by = user
            self.updated_by = user
        super().save(*args, **kwargs)


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
