from django.db import models
from django.utils import timezone

from core.models import AuditMixin


class TipoContato(models.TextChoices):
    LIGACAO = 'LIGACAO', 'Ligação'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'
    EMAIL = 'EMAIL', 'E-mail'
    VISITA = 'VISITA', 'Visita'
    REUNIAO = 'REUNIAO', 'Reunião'
    NEGOCIACAO = 'NEGOCIACAO', 'Negociação'
    PROPOSTA = 'PROPOSTA', 'Proposta'
    POS_VENDA = 'POS_VENDA', 'Pós-venda'
    RECLAMACAO = 'RECLAMACAO', 'Reclamação'
    OUTRO = 'OUTRO', 'Outro'


class Resultado(models.TextChoices):
    SEM_RESPOSTA = 'SEM_RESPOSTA', 'Sem resposta'
    CONTATO_REALIZADO = 'CONTATO_REALIZADO', 'Contato realizado'
    SEM_INTERESSE = 'SEM_INTERESSE', 'Sem interesse'
    INTERESSADO = 'INTERESSADO', 'Interessado'
    PROPOSTA_ENVIADA = 'PROPOSTA_ENVIADA', 'Proposta enviada'
    AGUARDANDO_RETORNO = 'AGUARDANDO_RETORNO', 'Aguardando retorno'
    PEDIDO_FECHADO = 'PEDIDO_FECHADO', 'Pedido fechado'
    POS_VENDA = 'POS_VENDA', 'Pós-venda'
    PENDENTE = 'PENDENTE', 'Sem resposta'  # legado — mesmo label


class HumorCliente(models.TextChoices):
    MUITO_RECEPTIVO = 'MUITO_RECEPTIVO', 'Muito receptivo'
    RECEPTIVO = 'RECEPTIVO', 'Receptivo'
    NEUTRO = 'NEUTRO', 'Neutro'
    RESISTENTE = 'RESISTENTE', 'Resistente'
    INSATISFEITO = 'INSATISFEITO', 'Insatisfeito'


class ProximaAcao(models.TextChoices):
    LIGAR = 'LIGAR', 'Ligar'
    ENVIAR_CATALOGO = 'ENVIAR_CATALOGO', 'Enviar catálogo'
    ENVIAR_PROPOSTA = 'ENVIAR_PROPOSTA', 'Enviar proposta'
    AGENDAR_VISITA = 'AGENDAR_VISITA', 'Agendar visita'
    ENVIAR_WHATSAPP = 'ENVIAR_WHATSAPP', 'Enviar WhatsApp'
    ENVIAR_EMAIL = 'ENVIAR_EMAIL', 'Enviar e-mail'
    SEM_ACAO = 'SEM_ACAO', 'Encerrar atendimento'


class AtividadeClienteQuerySet(models.QuerySet):
    def ativas(self):
        return self.filter(deleted_at__isnull=True)

    def para_usuario(self, usuario):
        qs = self.ativas()
        if usuario.is_admin:
            return qs
        return qs.filter(cliente__vendedor=usuario)

    def pendentes(self):
        return (
            self.ativas()
            .filter(concluida=False)
            .exclude(proxima_acao=ProximaAcao.SEM_ACAO)
            .exclude(data_proxima_acao__isnull=True)
        )

    def pendentes_para_usuario(self, usuario):
        return self.para_usuario(usuario).pendentes()

    def hoje(self):
        hoje = timezone.localdate()
        return self.pendentes().filter(data_proxima_acao=hoje)

    def atrasadas(self):
        hoje = timezone.localdate()
        return self.pendentes().filter(data_proxima_acao__lt=hoje)

    def proximas(self):
        hoje = timezone.localdate()
        return self.pendentes().filter(data_proxima_acao__gt=hoje)

    def ordenar_pendentes(self):
        return self.order_by('data_proxima_acao', 'hora_proxima_acao', 'cliente__nome')


class AtividadeCliente(AuditMixin, models.Model):
    cliente = models.ForeignKey(
        'clientes.Cliente',
        on_delete=models.CASCADE,
        related_name='atividades',
    )
    usuario = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.PROTECT,
        related_name='atividades_cliente',
    )
    tipo_contato = models.CharField(
        max_length=20,
        choices=TipoContato.choices,
        default=TipoContato.OUTRO,
    )
    assunto = models.CharField(max_length=255, blank=True)
    resumo = models.TextField()
    resultado = models.CharField(
        max_length=30,
        choices=Resultado.choices,
        default=Resultado.PENDENTE,
    )
    humor_cliente = models.CharField(
        max_length=20,
        choices=HumorCliente.choices,
        null=True,
        blank=True,
    )
    produtos_relacionados = models.ManyToManyField(
        'clientes.Produto',
        blank=True,
        related_name='atividades_relacionadas',
        verbose_name='produtos relacionados',
    )
    proxima_acao = models.CharField(
        max_length=30,
        choices=ProximaAcao.choices,
        default=ProximaAcao.SEM_ACAO,
    )
    data_proxima_acao = models.DateField(null=True, blank=True)
    hora_proxima_acao = models.TimeField(null=True, blank=True)
    concluida = models.BooleanField(default=False)
    valor_venda = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='valor da venda',
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atividades_excluidas',
    )

    objects = AtividadeClienteQuerySet.as_manager()

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'atividade do cliente'
        verbose_name_plural = 'atividades do cliente'

    def __str__(self):
        return f'{self.cliente.nome} — {self.get_tipo_contato_display()} ({self.data_criacao:%d/%m/%Y})'

    def delete(self, using=None, keep_parents=False, usuario=None):
        self.deleted_at = timezone.now()
        if usuario:
            self.deleted_by = usuario
        self.save(update_fields=['deleted_at', 'deleted_by', 'data_atualizacao'])

    def pode_editar(self, usuario):
        if usuario.is_admin:
            return True
        return self.usuario_id == usuario.pk

    @property
    def tem_followup_pendente(self):
        return (
            not self.concluida
            and self.proxima_acao != ProximaAcao.SEM_ACAO
            and self.data_proxima_acao is not None
        )


class AtividadeClienteEdicao(models.Model):
    atividade = models.ForeignKey(
        AtividadeCliente,
        on_delete=models.CASCADE,
        related_name='edicoes',
    )
    usuario = models.ForeignKey(
        'accounts.Usuario',
        on_delete=models.PROTECT,
        related_name='edicoes_atividade',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    alteracoes = models.JSONField(default=list)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'edição de atividade'
        verbose_name_plural = 'edições de atividade'

    def __str__(self):
        return f'Edição {self.atividade_id} por {self.usuario}'
