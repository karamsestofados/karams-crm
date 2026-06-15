from django.db import models


class ResultadoContato(models.TextChoices):
    CONTATO = 'contato', 'Contato'
    VENDA = 'venda', 'Venda'
    SEM_RESPOSTA = 'sem_resposta', 'Sem resposta'
    RETORNO = 'retorno', 'Retorno'
    PROPOSTA = 'proposta', 'Proposta'
    OBS = 'obs', 'Observação'


class RegistroDiario(models.Model):
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.CASCADE,
        related_name='registros_diarios',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_diarios',
    )
    cliente_nome_livre = models.CharField(
        max_length=255,
        blank=True,
        help_text='Nome livre quando cliente não está cadastrado',
    )
    data = models.DateField()
    resultado = models.CharField(max_length=20, choices=ResultadoContato.choices)
    observacao = models.TextField(blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'registro diário'
        verbose_name_plural = 'registros diários'

    def __str__(self):
        nome = self.cliente.nome if self.cliente else self.cliente_nome_livre
        return f'{nome} — {self.get_resultado_display()} ({self.data})'

    @property
    def nome_cliente(self):
        if self.cliente:
            return self.cliente.nome
        return self.cliente_nome_livre
