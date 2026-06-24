from datetime import timedelta

from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, StatusFunil
from relacionamento.models import AtividadeCliente


def calcular_indice_saude(pct_sem_contato, pct_negociacao_atrasada, pct_perdidos):
    """
    Índice 0–100: combina os três indicadores de problema de forma multiplicativa.
    Cada percentual reduz proporcionalmente a saúde restante da carteira.
    """
    indice = 100.0
    for pct in (pct_sem_contato, pct_negociacao_atrasada, pct_perdidos):
        indice *= 1 - (pct / 100)
    return max(0, min(100, round(indice)))


def classificar_indice_saude(indice):
    if indice >= 80:
        return {'label': 'Excelente', 'classe': 'excelente'}
    if indice >= 60:
        return {'label': 'Saudável', 'classe': 'saudavel'}
    if indice >= 40:
        return {'label': 'Atenção', 'classe': 'atencao'}
    if indice >= 20:
        return {'label': 'Risco', 'classe': 'risco'}
    return {'label': 'Crítica', 'classe': 'critica'}


def _metricas_carteira(qs_clientes, usuario):
    hoje = timezone.localdate()
    limite_30 = hoje - timedelta(days=30)
    total = qs_clientes.count()
    if total == 0:
        status = classificar_indice_saude(100)
        return {
            'total': 0,
            'indice': 100,
            'status_label': status['label'],
            'status_classe': status['classe'],
            'pct_sem_contato': 0,
            'pct_negociacao_atrasada': 0,
            'pct_perdidos': 0,
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

    def pct(n):
        return round(n / total * 100, 1)

    pct_sem_contato = pct(sem_contato)
    pct_negociacao_atrasada = pct(atrasadas)
    pct_perdidos = pct(perdidos)
    indice = calcular_indice_saude(pct_sem_contato, pct_negociacao_atrasada, pct_perdidos)
    status = classificar_indice_saude(indice)

    return {
        'total': total,
        'indice': indice,
        'status_label': status['label'],
        'status_classe': status['classe'],
        'sem_contato': sem_contato,
        'pct_sem_contato': pct_sem_contato,
        'negociacao_atrasada': atrasadas,
        'pct_negociacao_atrasada': pct_negociacao_atrasada,
        'perdidos': perdidos,
        'pct_perdidos': pct_perdidos,
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
