from django.db import models


class NotaRelacionamento(models.Model):
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.CASCADE,
        related_name='notas_relacionamento',
    )
    data = models.DateField()
    texto = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data']
        unique_together = [['cliente', 'data']]
        verbose_name = 'nota de relacionamento'
        verbose_name_plural = 'notas de relacionamento'

    def __str__(self):
        return f'{self.cliente.nome} — {self.data}'


class AlertaRetorno(models.Model):
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.CASCADE,
        related_name='alertas_retorno',
    )
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.CASCADE,
        related_name='alertas_retorno',
    )
    data_contato = models.DateField()
    data_alerta = models.DateField()
    dispensado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_alerta']
        verbose_name = 'alerta de retorno'
        verbose_name_plural = 'alertas de retorno'

    def __str__(self):
        return f'{self.cliente.nome} — alerta {self.data_alerta}'
