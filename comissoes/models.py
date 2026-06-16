import calendar
import math

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
    meta_clientes_novos = models.PositiveIntegerField(default=0)
    meta_propostas = models.PositiveIntegerField(default=0)
    meta_visitas = models.PositiveIntegerField(default=0)
    meta_vendas = models.DecimalField(max_digits=12, decimal_places=2, default=80000)
    observacoes = models.TextField(blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-ano', '-mes']
        unique_together = [['vendedor', 'mes', 'ano']]
        verbose_name = 'meta mensal'
        verbose_name_plural = 'metas mensais'

    def __str__(self):
        alvo = self.vendedor or 'Equipe'
        return f'{alvo} — {self.mes:02d}/{self.ano}'

    @property
    def usuario(self):
        return self.vendedor

    @property
    def meta_vendas_valor(self):
        return self.meta_vendas

    @property
    def meta_semanal_contatos(self):
        return math.ceil(self.meta_contatos / 4)

    @property
    def meta_dia_contatos(self):
        dias = calendar.monthrange(self.ano, self.mes)[1]
        return max(1, math.ceil(self.meta_contatos / dias))


class TipoConquista(models.TextChoices):
    PRIMEIRA_VENDA = 'primeira_venda', 'Primeira Venda'
    CEM_CONTATOS = 'cem_contatos', '100 Contatos'
    META_BATIDA = 'meta_batida', 'Meta Batida'
    TOP_MES = 'top_mes', 'Top do Mês'
    MAIOR_CRESCIMENTO = 'maior_crescimento', 'Maior Crescimento'


class ConquistaVendedor(models.Model):
    usuario = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.CASCADE,
        related_name='conquistas',
    )
    tipo = models.CharField(max_length=30, choices=TipoConquista.choices)
    mes = models.PositiveSmallIntegerField(null=True, blank=True)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    data_conquista = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_conquista']
        unique_together = [['usuario', 'tipo', 'mes', 'ano']]
        verbose_name = 'conquista'
        verbose_name_plural = 'conquistas'

    def __str__(self):
        return f'{self.usuario} — {self.get_tipo_display()}'
