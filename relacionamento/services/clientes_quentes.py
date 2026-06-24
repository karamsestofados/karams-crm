from datetime import timedelta

from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente, StatusFunil
from relacionamento.models import AtividadeCliente, Resultado


FUNIL_QUENTE = (
    StatusFunil.NEGOCIACAO,
    StatusFunil.PROPOSTA_ENVIADA,
    StatusFunil.AGUARDANDO_RETORNO,
    StatusFunil.EM_CONTATO,
)


def _formatar_ultimo_contato(dias):
    if dias == 0:
        return 'hoje'
    if dias == 1:
        return 'ontem'
    return f'há {dias} dias'


def _pontuar_cliente(cliente, ultima_atividade, hoje):
    if cliente.status_funil in (StatusFunil.CLIENTE_PERDIDO, StatusFunil.PEDIDO_FECHADO):
        return 0

    score = 0
    if ultima_atividade:
        dias = (hoje - ultima_atividade.data_criacao.date()).days
        if dias <= 3:
            score += 3
        if ultima_atividade.resultado in (Resultado.PROPOSTA_ENVIADA, Resultado.INTERESSADO):
            score += 2
        if ultima_atividade.concluida is False and ultima_atividade.proxima_acao != 'SEM_ACAO':
            score += 1
    if cliente.status_funil in FUNIL_QUENTE:
        score += 2
    return score


def listar_clientes_quentes(usuario, limit=6):
    hoje = timezone.localdate()
    qs = Cliente.objects.para_usuario(usuario).filter(
        categoria__in=(
            CategoriaCliente.ATIVO,
            CategoriaCliente.PROSPECCAO,
            CategoriaCliente.ADORMECIDO,
        ),
    ).exclude(
        status_funil__in=(StatusFunil.CLIENTE_PERDIDO, StatusFunil.PEDIDO_FECHADO),
    ).select_related('vendedor').annotate(
        total_interacoes=Count(
            'atividades',
            filter=Q(atividades__deleted_at__isnull=True),
        ),
    ).prefetch_related(
        Prefetch(
            'atividades',
            queryset=AtividadeCliente.objects.ativas().order_by('-data_criacao')[:1],
            to_attr='ultima_atividade_list',
        ),
    )

    candidatos = []
    for cliente in qs:
        ultima = cliente.ultima_atividade_list[0] if cliente.ultima_atividade_list else None
        score = _pontuar_cliente(cliente, ultima, hoje)
        if score <= 0:
            continue
        if ultima:
            dias = (hoje - ultima.data_criacao.date()).days
        else:
            dias = (hoje - cliente.created_at.date()).days if cliente.created_at else 999
        candidatos.append({
            'cliente': cliente,
            'score': score,
            'ultimo_contato_label': _formatar_ultimo_contato(dias),
            'total_interacoes': cliente.total_interacoes,
            'ultima_atividade': ultima,
        })

    candidatos.sort(key=lambda x: (-x['score'], x['cliente'].nome))
    return candidatos[:limit]
