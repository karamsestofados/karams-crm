from datetime import timedelta

from django.conf import settings

from clientes.models import Cliente
from relacionamento.models import AtividadeCliente


def calcular_giro_carteira(usuario, dias=None):
    """Percentual de clientes ativos com interação encerrada no período."""
    dias = dias or getattr(settings, 'GIRO_CARTEIRA_DIAS', 7)
    from django.utils import timezone

    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=dias - 1)

    carteira = Cliente.objects.para_usuario(usuario).ativos() if usuario else Cliente.objects.ativos()
    total_clientes = carteira.count()

    atividades = AtividadeCliente.objects.ativas().filter(
        concluida=True,
        data_criacao__date__gte=inicio,
        data_criacao__date__lte=hoje,
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
        'periodo_dias': dias,
    }
