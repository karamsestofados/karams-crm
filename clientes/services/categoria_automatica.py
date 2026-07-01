from datetime import date, datetime, timedelta

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente, HistoricoInteracao
from relacionamento.models import AtividadeCliente


def _dias_limite():
    return getattr(settings, 'ADORMECIMENTO_DIAS', 30)


def _limite_datetime(dias=None):
    dias = dias if dias is not None else _dias_limite()
    return timezone.now() - timedelta(days=dias)


def _as_date(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return None


def ultima_data_contato_cliente(cliente):
    """Data mais recente entre Atividade Diária e histórico legado."""
    ultima_atividade = (
        AtividadeCliente.objects.ativas()
        .filter(cliente=cliente)
        .order_by('-data_criacao')
        .values_list('data_criacao', flat=True)
        .first()
    )
    ultima_historico = (
        HistoricoInteracao.objects.filter(cliente=cliente)
        .order_by('-data', '-created_at')
        .values_list('data', flat=True)
        .first()
    )
    datas = [d for d in (_as_date(ultima_atividade), ultima_historico) if d is not None]
    return max(datas) if datas else None


def _queryset_ativos_elegiveis_adormecido(dias=None):
    """Clientes Ativos sem contato há `dias` (atividade ou histórico legado)."""
    limite = _limite_datetime(dias)
    limite_data = limite.date()

    return (
        Cliente.objects.filter(categoria=CategoriaCliente.ATIVO)
        .annotate(
            ultima_atividade=Max(
                'atividades__data_criacao',
                filter=Q(atividades__deleted_at__isnull=True),
            ),
            ultima_historico=Max('historico__data'),
        )
        .filter(Q(ultima_atividade__isnull=True) | Q(ultima_atividade__lt=limite))
        .filter(Q(ultima_historico__isnull=True) | Q(ultima_historico__lt=limite_data))
        .filter(
            Q(ultima_atividade__isnull=False)
            | Q(ultima_historico__isnull=False)
            | Q(created_at__lte=limite),
        )
    )


def reativar_cliente_apos_interacao(cliente):
    if cliente.categoria == CategoriaCliente.INATIVO:
        return False
    if cliente.categoria == CategoriaCliente.ATIVO:
        return False
    cliente.categoria = CategoriaCliente.ATIVO
    cliente.save(update_fields=['categoria', 'updated_at'])
    return True


def processar_clientes_adormecidos(dias=None):
    return _queryset_ativos_elegiveis_adormecido(dias).update(
        categoria=CategoriaCliente.ADORMECIDO,
    )


def cliente_sem_contato(cliente, dias=None, hoje=None):
    """Indica se o cliente está há `dias` ou mais sem qualquer interação."""
    dias = dias if dias is not None else _dias_limite()
    limite = _limite_datetime(dias)
    ultima = ultima_data_contato_cliente(cliente)
    if ultima:
        return ultima < limite.date()
    created = cliente.created_at
    if not created:
        return False
    return created <= limite


def auditar_adormecidos(dias=None, amostra=15):
    """
    Resumo para dry-run: totais por categoria e clientes que seriam movidos.
    Não altera o banco.
    """
    dias = dias if dias is not None else _dias_limite()
    limite = _limite_datetime(dias)

    por_categoria = {
        cat: Cliente.objects.filter(categoria=cat).count()
        for cat, _ in CategoriaCliente.choices
    }

    elegiveis = list(
        _queryset_ativos_elegiveis_adormecido(dias)
        .select_related('vendedor')
        .order_by('nome')[:amostra]
    )
    total_elegiveis = _queryset_ativos_elegiveis_adormecido(dias).count()

    amostra_detalhes = []
    for cliente in elegiveis:
        ua = getattr(cliente, 'ultima_atividade', None)
        uh = getattr(cliente, 'ultima_historico', None)
        if ua is None and uh is None:
            motivo = 'sem atividade nem histórico legado'
        else:
            motivo = 'último contato há mais de {} dias'.format(dias)
        amostra_detalhes.append({
            'id': cliente.pk,
            'nome': cliente.nome,
            'vendedor': cliente.vendedor.get_full_name() or cliente.vendedor.username,
            'ultima_atividade': ua,
            'ultima_historico': uh,
            'created_at': cliente.created_at,
            'motivo': motivo,
        })

    return {
        'dias': dias,
        'limite': limite,
        'por_categoria': por_categoria,
        'total_elegiveis': total_elegiveis,
        'amostra': amostra_detalhes,
        'ativos_total': por_categoria.get(CategoriaCliente.ATIVO, 0),
    }
