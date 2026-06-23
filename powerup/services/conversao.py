from accounts.models import Papel, Usuario
from clientes.models import Cliente
from comissoes.models import Venda
from comissoes.services.produtividade import calcular_realizado
from relacionamento.models import AtividadeCliente, Resultado


def _taxa_pct(fechados, orcamentos):
    if orcamentos <= 0:
        return 0
    return round(fechados / orcamentos * 100, 1)


def conversao_por_vendedor(de, ate, usuario_viewer):
    if usuario_viewer.is_admin:
        vendedores = Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True).order_by('first_name')
    else:
        vendedores = Usuario.objects.filter(pk=usuario_viewer.pk)

    linhas = []
    mes_ref = de.month if de else None
    ano_ref = de.year if de else None
    for v in vendedores:
        realizado = calcular_realizado(
            v,
            mes_ref or 1,
            ano_ref or 2000,
            de=de,
            ate=ate,
        )
        leads = Cliente.objects.filter(vendedor=v)
        if de and ate:
            leads = leads.filter(created_at__date__gte=de, created_at__date__lte=ate)
        leads_count = leads.count()

        orcamentos = realizado['propostas']
        fechamentos = AtividadeCliente.objects.ativas().filter(
            cliente__vendedor=v,
            resultado=Resultado.PEDIDO_FECHADO,
            data_criacao__date__gte=de,
            data_criacao__date__lte=ate,
        ).count()
        vendas_count = Venda.objects.filter(
            vendedor=v, data__gte=de, data__lte=ate,
        ).count()
        fechados = max(fechamentos, vendas_count)

        linhas.append({
            'vendedor': v,
            'nome': v.get_full_name() or v.username,
            'leads': leads_count,
            'orcamentos': orcamentos,
            'fechamentos': fechados,
            'taxa_pct': _taxa_pct(fechados, orcamentos),
        })
    return linhas
