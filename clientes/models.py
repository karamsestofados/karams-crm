from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
from django.utils import timezone

from core.models import AuditMixin


class TipoProduto(models.TextChoices):
    PADRAO = 'PADRAO', 'Padrão'
    EXCLUSIVO = 'EXCLUSIVO', 'Exclusivo'
    UNICO = 'UNICO', 'Único'


class ProdutoQuerySet(models.QuerySet):
    def exclusivos(self):
        return self.filter(tipo_produto=TipoProduto.EXCLUSIVO)

    def unicos(self):
        return self.filter(tipo_produto=TipoProduto.UNICO)

    def padrao(self):
        return self.filter(tipo_produto=TipoProduto.PADRAO)

    def ativos(self):
        return self.filter(ativo=True)

    def sem_cliente(self):
        return self.ativos().annotate(
            total_clientes=Count('vinculos_cliente'),
        ).filter(total_clientes=0)

    def com_total_clientes(self):
        return self.annotate(total_clientes=Count('vinculos_cliente'))


class Produto(AuditMixin, models.Model):
    nome = models.CharField(max_length=150, unique=True)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=100, blank=True)
    tipo_produto = models.CharField(
        max_length=20,
        choices=TipoProduto.choices,
        default=TipoProduto.PADRAO,
    )
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    novo = models.BooleanField(default=False)
    usuario_responsavel = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos_responsaveis',
    )

    objects = ProdutoQuerySet.as_manager()

    class Meta:
        ordering = ['nome']
        verbose_name = 'produto'
        verbose_name_plural = 'produtos'

    def __str__(self):
        return self.nome


class CategoriaCliente(models.TextChoices):
    ATIVO = 'ativo', 'Ativo'
    ADORMECIDO = 'adormecido', 'Adormecido'
    PROSPECCAO = 'prospeccao', 'Prospecção'
    INATIVO = 'inativo', 'Inativo'


class TipoCliente(models.TextChoices):
    LOJA_MOVEIS = 'LOJA_MOVEIS', 'Loja de Móveis'
    ARQUITETO = 'ARQUITETO', 'Arquiteto'
    DESIGNER_INTERIORES = 'DESIGNER_INTERIORES', 'Designer de Interiores'
    REVENDA = 'REVENDA', 'Revenda'
    MARKETPLACE = 'MARKETPLACE', 'Marketplace'
    HOTELARIA = 'HOTELARIA', 'Hotelaria'
    CORPORATIVO = 'CORPORATIVO', 'Corporativo'
    CONSUMIDOR_FINAL = 'CONSUMIDOR_FINAL', 'Consumidor Final'
    OUTROS = 'OUTROS', 'Outros'


class ModalidadeCliente(models.TextChoices):
    RECORRENTE = 'RECORRENTE', 'Recorrente'
    COMPRA_UNICA = 'COMPRA_UNICA', 'Compra Única'


class SegmentoCliente(models.TextChoices):
    MOVEIS = 'MOVEIS', 'Móveis'
    ESTOFADOS = 'ESTOFADOS', 'Estofados'
    VAREJO = 'VAREJO', 'Varejo'
    ALTO_PADRAO = 'ALTO_PADRAO', 'Alto Padrão'
    DECORACAO = 'DECORACAO', 'Decoração'
    PLANEJADOS = 'PLANEJADOS', 'Planejados'
    CORPORATIVO = 'CORPORATIVO', 'Corporativo'
    HOTELARIA = 'HOTELARIA', 'Hotelaria'
    E_COMMERCE = 'E_COMMERCE', 'E-commerce'
    OUTROS = 'OUTROS', 'Outros'


class OrigemLead(models.TextChoices):
    INSTAGRAM = 'INSTAGRAM', 'Instagram'
    FACEBOOK = 'FACEBOOK', 'Facebook'
    GOOGLE = 'GOOGLE', 'Google'
    SITE = 'SITE', 'Site'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    INDICACAO = 'INDICACAO', 'Indicação'
    REPRESENTANTE = 'REPRESENTANTE', 'Representante'
    CLIENTE_ANTIGO = 'CLIENTE_ANTIGO', 'Cliente Antigo'
    TELEMARKETING = 'TELEMARKETING', 'Telemarketing'
    FEIRA = 'FEIRA', 'Feira'
    PESQUISA = 'PESQUISA', 'Pesquisa'
    OUTROS = 'OUTROS', 'Outros'


class StatusFunil(models.TextChoices):
    LEAD_NOVO = 'LEAD_NOVO', 'Lead Novo'
    EM_CONTATO = 'EM_CONTATO', 'Em Contato'
    PROPOSTA_ENVIADA = 'PROPOSTA_ENVIADA', 'Proposta Enviada'
    NEGOCIACAO = 'NEGOCIACAO', 'Negociação'
    AGUARDANDO_RETORNO = 'AGUARDANDO_RETORNO', 'Aguardando Retorno'
    PEDIDO_FECHADO = 'PEDIDO_FECHADO', 'Pedido Fechado'
    CLIENTE_ATIVO = 'CLIENTE_ATIVO', 'Cliente Ativo'
    CLIENTE_PERDIDO = 'CLIENTE_PERDIDO', 'Cliente Perdido'


class RegiaoAtuacao(models.TextChoices):
    NORTE = 'NORTE', 'Norte'
    NORDESTE = 'NORDESTE', 'Nordeste'
    CENTRO_OESTE = 'CENTRO_OESTE', 'Centro-Oeste'
    SUDESTE = 'SUDESTE', 'Sudeste'
    SUL = 'SUL', 'Sul'


class ClienteQuerySet(models.QuerySet):
    def para_usuario(self, usuario):
        if usuario.is_admin:
            return self
        return self.filter(vendedor=usuario)

    def ativos(self):
        return self.exclude(categoria=CategoriaCliente.INATIVO)


class Cliente(AuditMixin, models.Model):
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.PROTECT,
        related_name='clientes',
        verbose_name='vendedor responsável',
    )
    categoria = models.CharField(
        max_length=20,
        choices=CategoriaCliente.choices,
        default=CategoriaCliente.ATIVO,
    )
    nome = models.CharField(max_length=255)
    tipo_cliente = models.CharField(
        max_length=30,
        choices=TipoCliente.choices,
        null=True,
        blank=True,
        verbose_name='Perfil do Cliente',
    )
    modalidade_cliente = models.CharField(
        max_length=20,
        choices=ModalidadeCliente.choices,
        null=True,
        blank=True,
        verbose_name='Tipo Cliente',
    )
    segmento = models.CharField(
        max_length=30,
        choices=SegmentoCliente.choices,
        null=True,
        blank=True,
    )
    origem_lead = models.CharField(
        max_length=30,
        choices=OrigemLead.choices,
        null=True,
        blank=True,
    )
    status_funil = models.CharField(
        max_length=30,
        choices=StatusFunil.choices,
        default=StatusFunil.LEAD_NOVO,
    )
    regiao_atuacao = models.CharField(
        max_length=20,
        choices=RegiaoAtuacao.choices,
        null=True,
        blank=True,
    )
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField(max_length=9, blank=True, default='')
    telefone = models.CharField(max_length=50, blank=True)
    responsavel = models.CharField(max_length=150, blank=True)
    instagram = models.CharField(max_length=150, blank=True)
    endereco = models.TextField(blank=True)
    data_primeiro_contato = models.DateField(null=True, blank=True)
    feedback_original = models.TextField(blank=True)
    legacy_id = models.CharField(max_length=20, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ClienteQuerySet.as_manager()

    class Meta:
        ordering = ['nome']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return self.nome

    @property
    def is_inativo(self):
        return self.categoria == CategoriaCliente.INATIVO

    @property
    def instagram_url(self):
        if self.instagram:
            return f'https://instagram.com/{self.instagram}'
        return ''

    @property
    def ultima_interacao(self):
        try:
            return self.atividades.filter(deleted_at__isnull=True).order_by('-data_criacao').first()
        except Exception:
            return self.historico.order_by('-data', '-created_at').first()

    @property
    def dias_desde_ultimo_contato(self):
        ultima = self.ultima_interacao
        if not ultima:
            return None
        from django.utils import timezone
        data_ref = getattr(ultima, 'data_criacao', None) or getattr(ultima, 'data', None)
        if hasattr(data_ref, 'date'):
            data_ref = data_ref.date()
        return (timezone.localdate() - data_ref).days

    @property
    def compra_unica(self):
        return self.historico.filter(tipo=TipoInteracao.VENDA).count() == 1


class ClienteProduto(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='vinculos_produto',
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='vinculos_cliente',
    )
    data_inicio = models.DateField(auto_now_add=True)
    observacoes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('cliente', 'produto')]
        ordering = ['-data_inicio']
        verbose_name = 'vínculo cliente-produto'
        verbose_name_plural = 'vínculos cliente-produto'

    def __str__(self):
        return f'{self.cliente.nome} — {self.produto.nome}'

    def clean(self):
        if self.produto.tipo_produto == TipoProduto.UNICO:
            existing = ClienteProduto.objects.filter(produto=self.produto)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                outro = existing.select_related('cliente').first()
                raise ValidationError(
                    f'Produto único "{self.produto.nome}" já está vinculado a '
                    f'"{outro.cliente.nome}". Não é possível vincular a outro cliente.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProdutoExclusividade(models.Model):
    """Base para controle territorial e alertas de renovação de exclusividade."""
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='exclusividades',
    )
    regiao = models.CharField(
        max_length=20,
        choices=RegiaoAtuacao.choices,
        blank=True,
    )
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    observacoes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inicio']
        verbose_name = 'exclusividade de produto'
        verbose_name_plural = 'exclusividades de produto'

    def __str__(self):
        return f'{self.produto.nome} — {self.get_regiao_display() or "Geral"}'


class TipoInteracao(models.TextChoices):
    VENDA = 'venda', 'Venda'
    CONTATO = 'contato', 'Contato'
    RETORNO = 'retorno', 'Retorno'
    PROPOSTA = 'proposta', 'Proposta'
    SEM_RESPOSTA = 'sem_resposta', 'Sem resposta'
    OBS = 'obs', 'Observação'


class HistoricoInteracao(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='historico',
    )
    vendedor = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.PROTECT,
        related_name='interacoes',
    )
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TipoInteracao.choices)
    produtos = models.ManyToManyField(Produto, blank=True)
    observacao = models.TextField(blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']
        verbose_name = 'histórico de interação'
        verbose_name_plural = 'históricos de interação'

    def __str__(self):
        return f'{self.cliente.nome} — {self.get_tipo_display()} ({self.data})'
