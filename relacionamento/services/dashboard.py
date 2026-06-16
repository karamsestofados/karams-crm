from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente
from relacionamento.models import AtividadeCliente, Resultado


def kpis_relacionamento(usuario):
    hoje = timezone.localdate()
    inicio_semana = hoje - timedelta(days=6)
    inicio_mes = hoje.replace(day=1)

    atividades = AtividadeCliente.objects.para_usuario(usuario)

    contatos_hoje = atividades.filter(data_criacao__date=hoje).count()
    interacoes_semana = atividades.filter(data_criacao__date__gte=inicio_semana).count()
    pedidos_fechados_mes = atividades.filter(
        data_criacao__date__gte=inicio_mes,
        resultado=Resultado.PEDIDO_FECHADO,
    ).count()
    negociacoes_abertas = atividades.filter(
        Q(resultado=Resultado.AGUARDANDO_RETORNO) | Q(concluida=False)
    ).exclude(
        proxima_acao='SEM_ACAO',
    ).count()

    clientes = Cliente.objects.para_usuario(usuario).ativos()
    limite_30 = hoje - timedelta(days=30)
    clientes_com_atividade = atividades.filter(
        data_criacao__date__gte=limite_30,
    ).values('cliente_id').distinct()
    sem_contato_30 = clientes.exclude(
        pk__in=clientes_com_atividade,
    ).count()

    return {
        'contatos_hoje': contatos_hoje,
        'interacoes_semana': interacoes_semana,
        'clientes_sem_contato_30': sem_contato_30,
        'negociacoes_abertas': negociacoes_abertas,
        'pedidos_fechados_mes': pedidos_fechados_mes,
    }
