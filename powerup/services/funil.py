from django.db.models import Count, Q

from clientes.models import CategoriaCliente, Cliente, StatusFunil


def funil_comercial(usuario, de=None, ate=None):
    qs = Cliente.objects.para_usuario(usuario).exclude(
        categoria=CategoriaCliente.INATIVO,
    )
    if de and ate:
        qs = qs.filter(
            Q(atividades__data_criacao__date__gte=de, atividades__data_criacao__date__lte=ate)
            | Q(created_at__date__gte=de, created_at__date__lte=ate),
        ).distinct()

    contagens = dict(
        qs.values('status_funil').annotate(total=Count('id')).values_list('status_funil', 'total'),
    )

    leads = contagens.get(StatusFunil.LEAD_NOVO, 0)
    prospectados = contagens.get(StatusFunil.EM_CONTATO, 0)
    orcamentos = sum(
        contagens.get(s, 0)
        for s in (
            StatusFunil.PROPOSTA_ENVIADA,
            StatusFunil.NEGOCIACAO,
            StatusFunil.AGUARDANDO_RETORNO,
        )
    )
    fechamentos = sum(
        contagens.get(s, 0)
        for s in (StatusFunil.PEDIDO_FECHADO, StatusFunil.CLIENTE_ATIVO)
    )

    etapas = [
        {'label': 'Leads', 'total': leads},
        {'label': 'Prospectados', 'total': prospectados},
        {'label': 'Orçamentos', 'total': orcamentos},
        {'label': 'Fechamentos', 'total': fechamentos},
    ]
    max_total = max((e['total'] for e in etapas), default=1) or 1
    for e in etapas:
        e['largura_pct'] = max(25, round(e['total'] / max_total * 100))
    return etapas
