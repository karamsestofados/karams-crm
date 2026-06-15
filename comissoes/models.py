from django.db import models


class Venda(models.Model):
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.PROTECT,
        related_name='vendas',
    )
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.PROTECT,
        related_name='vendas',
    )
    data = models.DateField()
    produtos_texto = models.CharField(max_length=500, blank=True)
    produtos = models.ManyToManyField('clientes.Produto', blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'venda'
        verbose_name_plural = 'vendas'

    def __str__(self):
        return f'{self.cliente.nome} — R$ {self.valor} ({self.data})'


class MetaMensal(models.Model):
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='metas_mensais',
        help_text='Vazio = meta geral da equipe',
    )
    mes = models.PositiveSmallIntegerField()
    ano = models.PositiveSmallIntegerField()
    meta_contatos = models.PositiveIntegerField(default=60)
    meta_vendas = models.DecimalField(max_digits=12, decimal_places=2, default=80000)

    class Meta:
        ordering = ['-ano', '-mes']
        unique_together = [['vendedor', 'mes', 'ano']]
        verbose_name = 'meta mensal'
        verbose_name_plural = 'metas mensais'

    def __str__(self):
        alvo = self.vendedor or 'Equipe'
        return f'{alvo} — {self.mes:02d}/{self.ano}'

    @property
    def meta_semanal_contatos(self):
        import math
        return math.ceil(self.meta_contatos / 4)
