from relacionamento.models import AtividadeCliente, AtividadeClienteEdicao


def montar_timeline_cliente(cliente, tipo_filtro='', limit=50):
    atividades = AtividadeCliente.objects.ativas().filter(cliente=cliente).select_related(
        'usuario',
    ).prefetch_related('produtos_relacionados').order_by('-data_criacao')
    if tipo_filtro:
        atividades = atividades.filter(tipo_contato=tipo_filtro)

    atividade_ids = list(atividades.values_list('pk', flat=True))
    edicoes = AtividadeClienteEdicao.objects.filter(
        atividade_id__in=atividade_ids,
    ).select_related('usuario', 'atividade')

    eventos = []
    for atividade in atividades:
        eventos.append({
            'tipo': 'interacao',
            'data': atividade.data_criacao,
            'atividade': atividade,
        })
    for edicao in edicoes:
        eventos.append({
            'tipo': 'edicao',
            'data': edicao.criado_em,
            'edicao': edicao,
        })

    eventos.sort(key=lambda e: e['data'], reverse=True)
    if limit:
        eventos = eventos[:limit]
    return eventos
