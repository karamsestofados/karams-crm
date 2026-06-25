import calendar
from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente
from relacionamento.models import AtividadeCliente
from relacionamento.services.dashboard import kpis_relacionamento
from relacionamento.services.rotina_diaria import rotina_diaria_para_usuario

MESES_PT = [
    '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def _atividades_qs(usuario):
    return (
        AtividadeCliente.objects
        .para_usuario(usuario)
        .select_related('cliente', 'cliente__vendedor', 'usuario')
        .prefetch_related('produtos_relacionados')
    )


def _pendentes_qs(usuario):
    return (
        _atividades_qs(usuario)
        .pendentes()
        .order_by('data_proxima_acao', 'hora_proxima_acao', 'cliente__nome')
    )


def resumo_dia(usuario):
    rotina = rotina_diaria_para_usuario(usuario)
    hoje = timezone.localdate()

    atividades_hoje = _atividades_qs(usuario).filter(data_criacao__date=hoje)
    interacoes_hoje = atividades_hoje.count()
    clientes_atendidos_hoje = atividades_hoje.values('cliente_id').distinct().count()

    kpis = kpis_relacionamento(usuario)

    return {
        **rotina,
        'total_hoje': rotina['hoje'].count(),
        'total_atrasadas': rotina['atrasadas'].count(),
        'total_proximas': rotina['proximas'].count(),
        'interacoes_hoje': interacoes_hoje,
        'clientes_atendidos_hoje': clientes_atendidos_hoje,
        'kpis': kpis,
        'data_hoje': hoje,
    }


def _dias_sem_contato_cliente(cliente, hoje=None):
    hoje = hoje or timezone.localdate()
    dias = cliente.dias_desde_ultimo_contato
    if dias is not None:
        return dias
    created = cliente.created_at
    if created:
        ref = created.date() if hasattr(created, 'date') else created
        return (hoje - ref).days
    return None


def _data_ultimo_contato(cliente, ultima_atividade):
    if ultima_atividade:
        dt = ultima_atividade.data_criacao
        if hasattr(dt, 'date'):
            return dt.date()
        return dt
    return None


def clientes_sem_contato(usuario, dias=30, limit=20, filtros_cliente=None):
    from comissoes.services.produtividade import _aplicar_filtros_cliente

    hoje = timezone.localdate()
    limite = timezone.now() - timezone.timedelta(days=dias)
    clientes = Cliente.objects.para_usuario(usuario).ativos().exclude(
        categoria=CategoriaCliente.INATIVO,
    ).select_related('vendedor')
    if filtros_cliente:
        clientes = _aplicar_filtros_cliente(clientes, filtros_cliente)

    sem_contato = []
    for cliente in clientes.iterator():
        ultima = (
            AtividadeCliente.objects.ativas()
            .filter(cliente=cliente)
            .order_by('-data_criacao')
            .first()
        )
        if ultima and ultima.data_criacao >= limite:
            continue
        dias_sem = _dias_sem_contato_cliente(cliente, hoje)
        if dias_sem is None or dias_sem >= dias:
            sem_contato.append({
                'cliente': cliente,
                'ultima_atividade': ultima,
                'data_ultimo_contato': _data_ultimo_contato(cliente, ultima),
                'dias_sem_contato': dias_sem if dias_sem is not None else 0,
            })

    sem_contato.sort(key=lambda x: x['dias_sem_contato'], reverse=True)
    return sem_contato[:limit]


def ultimas_interacoes(usuario, limit=15):
    return (
        _atividades_qs(usuario)
        .order_by('-data_criacao')[:limit]
    )


def _status_compromisso(data_ref, hoje):
    if data_ref < hoje:
        return 'atrasado'
    if data_ref == hoje:
        return 'hoje'
    return 'futuro'


def eventos_do_dia(usuario, data):
    """Compromissos agendados (follow-up pendente) + interações registradas na data."""
    compromissos = list(_pendentes_qs(usuario).filter(data_proxima_acao=data))
    interacoes = list(
        _atividades_qs(usuario)
        .filter(data_criacao__date=data)
        .order_by('-data_criacao')
    )
    return {
        'compromissos': compromissos,
        'interacoes': interacoes,
    }


def calendario_mensal(usuario, ano, mes):
    hoje = timezone.localdate()

    pendentes = list(_pendentes_qs(usuario).filter(
        data_proxima_acao__year=ano,
        data_proxima_acao__month=mes,
    ))

    por_dia_compromissos = {}
    for atv in pendentes:
        dia = atv.data_proxima_acao.day
        por_dia_compromissos.setdefault(dia, {'atrasado': 0, 'hoje': 0, 'futuro': 0})
        status = _status_compromisso(atv.data_proxima_acao, hoje)
        por_dia_compromissos[dia][status] += 1

    por_dia_interacoes = {}
    interacoes_mes = (
        _atividades_qs(usuario)
        .filter(data_criacao__year=ano, data_criacao__month=mes)
        .annotate(dia_local=TruncDate('data_criacao'))
        .values('dia_local')
        .annotate(total=Count('id'))
    )
    for row in interacoes_mes:
        if row['dia_local']:
            por_dia_interacoes[row['dia_local'].day] = row['total']

    cal = calendar.Calendar(firstweekday=6)
    semanas_raw = cal.monthdayscalendar(ano, mes)
    semanas = []
    for semana in semanas_raw:
        row = []
        for dia_num in semana:
            if dia_num == 0:
                row.append({'empty': True})
            else:
                comp = por_dia_compromissos.get(dia_num, {'atrasado': 0, 'hoje': 0, 'futuro': 0})
                row.append({
                    'empty': False,
                    'day': dia_num,
                    'date': date(ano, mes, dia_num),
                    'indicators': {
                        **comp,
                        'interacoes': por_dia_interacoes.get(dia_num, 0),
                    },
                    'is_today': hoje == date(ano, mes, dia_num),
                })
        semanas.append(row)

    return {
        'ano': ano,
        'mes': mes,
        'mes_nome': MESES_PT[mes],
        'semanas': semanas,
        'hoje': hoje,
    }


def contexto_cockpit_completo(usuario, ano=None, mes=None, dia_selecionado=None):
    hoje = timezone.localdate()
    ano = ano or hoje.year
    mes = mes or hoje.month
    dia_selecionado = dia_selecionado or hoje

    ctx = resumo_dia(usuario)
    ctx['calendario'] = calendario_mensal(usuario, ano, mes)
    ctx['dia_selecionado'] = dia_selecionado
    ctx['eventos_dia'] = eventos_do_dia(usuario, dia_selecionado)
    from relacionamento.services.insights import gerar_insights_cockpit
    ctx['insights'] = gerar_insights_cockpit(usuario)
    ctx['ultimas_interacoes'] = ultimas_interacoes(usuario)
    from comissoes.services.produtividade import meta_do_dia
    ctx['meta_dia'] = meta_do_dia(usuario)
    return ctx
