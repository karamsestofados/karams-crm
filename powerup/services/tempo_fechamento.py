from datetime import timedelta

from django.db.models import Min

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from comissoes.models import Venda
from relacionamento.models import AtividadeCliente, Resultado


def _dias_ate_fechamento(cliente, data_fechamento):
    inicio = cliente.data_primeiro_contato or (
        cliente.created_at.date() if cliente.created_at else data_fechamento
    )
    return max(0, (data_fechamento - inicio).days)


def tempo_medio_fechamento(de, ate, usuario_viewer):
    if usuario_viewer.is_admin:
        vendedores = Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True).order_by('first_name')
    else:
        vendedores = Usuario.objects.filter(pk=usuario_viewer.pk)

    resultado = []
    for v in vendedores:
        dias_lista = []

        vendas = Venda.objects.filter(vendedor=v, data__gte=de, data__lte=ate).select_related('cliente')
        for venda in vendas:
            dias_lista.append(_dias_ate_fechamento(venda.cliente, venda.data))

        atividades = AtividadeCliente.objects.ativas().filter(
            usuario=v,
            resultado=Resultado.PEDIDO_FECHADO,
            data_criacao__date__gte=de,
            data_criacao__date__lte=ate,
        ).values('cliente_id').annotate(primeira=Min('data_criacao'))

        cliente_ids_venda = {v.cliente_id for v in vendas}
        for row in atividades:
            if row['cliente_id'] in cliente_ids_venda:
                continue
            cliente = Cliente.objects.filter(pk=row['cliente_id']).first()
            if cliente:
                dias_lista.append(_dias_ate_fechamento(cliente, row['primeira'].date()))

        media = round(sum(dias_lista) / len(dias_lista)) if dias_lista else None
        resultado.append({
            'vendedor': v,
            'nome': v.get_full_name() or v.username,
            'dias_medio': media,
            'total_fechamentos': len(dias_lista),
        })
    return resultado
