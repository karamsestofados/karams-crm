import calendar
from datetime import date

from django.utils import timezone

from clientes.models import Cliente
from relacionamento.models import AtividadeCliente


def calcular_giro_carteira(usuario, mes=None, ano=None):
    """Percentual de clientes da carteira com interação encerrada no mês calendário."""
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year
    ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1)
    fim = min(hoje, date(ano, mes, ultimo_dia_mes)) if (ano, mes) == (hoje.year, hoje.month) else date(ano, mes, ultimo_dia_mes)

    carteira = Cliente.objects.para_usuario(usuario).ativos() if usuario else Cliente.objects.ativos()
    total_clientes = carteira.count()

    atividades = AtividadeCliente.objects.ativas().filter(
        concluida=True,
        data_criacao__date__gte=inicio,
        data_criacao__date__lte=fim,
    )
    if usuario:
        atividades = atividades.para_usuario(usuario)

    clientes_contatados = atividades.values('cliente_id').distinct().count()

    if total_clientes == 0:
        percentual = 0.0
    else:
        percentual = round(clientes_contatados / total_clientes * 100, 1)

    return {
        'total_clientes': total_clientes,
        'clientes_contatados': clientes_contatados,
        'percentual': percentual,
        'mes': mes,
        'ano': ano,
        'periodo_label': f'{mes:02d}/{ano}',
    }
