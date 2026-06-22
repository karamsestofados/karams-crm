from datetime import timedelta

from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, StatusFunil
from relacionamento.models import AtividadeCliente


def _metricas_carteira(qs_clientes, usuario):
    hoje = timezone.localdate()
    limite_30 = hoje - timedelta(days=30)
    total = qs_clientes.count()
    if total == 0:
        return {
            'total': 0,
            'pct_saudavel': 0,
            'pct_sem_contato': 0,
            'pct_perdidos': 0,
            'pct_negociacao_atrasada': 0,
        }

    perdidos = qs_clientes.filter(status_funil=StatusFunil.CLIENTE_PERDIDO).count()

    com_atividade = AtividadeCliente.objects.ativas().filter(
        cliente__in=qs_clientes,
        data_criacao__date__gte=limite_30,
    ).values('cliente_id').distinct()
    ids_com_atividade = {row['cliente_id'] for row in com_atividade}
    sem_contato = qs_clientes.exclude(pk__in=ids_com_atividade).exclude(
        status_funil=StatusFunil.CLIENTE_PERDIDO,
    ).count()

    atrasadas = AtividadeCliente.objects.ativas().pendentes_para_usuario(usuario).filter(
        cliente__in=qs_clientes,
        data_proxima_acao__lt=hoje,
    ).values('cliente_id').distinct().count()

    saudaveis = total - perdidos - sem_contato - atrasadas
    saudaveis = max(0, saudaveis)

    def pct(n):
        return round(n / total * 100, 1)

    return {
        'total': total,
        'saudaveis': saudaveis,
        'pct_saudavel': pct(saudaveis),
        'sem_contato': sem_contato,
        'pct_sem_contato': pct(sem_contato),
        'perdidos': perdidos,
        'pct_perdidos': pct(perdidos),
        'negociacao_atrasada': atrasadas,
        'pct_negociacao_atrasada': pct(atrasadas),
    }


def saude_carteira(usuario):
    base = Cliente.objects.para_usuario(usuario).exclude(
        categoria=CategoriaCliente.INATIVO,
    )
    propria = _metricas_carteira(base, usuario)

    por_vendedor = []
    if usuario.is_admin:
        for v in Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True).order_by('first_name'):
            qs = base.filter(vendedor=v)
            m = _metricas_carteira(qs, v)
            if m['total'] > 0:
                por_vendedor.append({
                    'vendedor': v,
                    'nome': v.get_full_name() or v.username,
                    **m,
                })

    return {
        'propria': propria,
        'por_vendedor': por_vendedor,
        'equipe': _metricas_carteira(base, usuario) if usuario.is_admin else None,
    }
