from django.db.models import Count

from clientes.models import Cliente, MotivoPerda, StatusFunil


def relatorio_motivo_perda(usuario, de=None, ate=None):
    qs = Cliente.objects.para_usuario(usuario).filter(
        status_funil=StatusFunil.CLIENTE_PERDIDO,
    ).exclude(motivo_perda='')

    if de and ate:
        qs = qs.filter(updated_at__date__gte=de, updated_at__date__lte=ate)

    total = qs.count()
    if total == 0:
        return {'total': 0, 'itens': []}

    agg = (
        qs.values('motivo_perda')
        .annotate(qtd=Count('id'))
        .order_by('-qtd')
    )
    itens = []
    for row in agg:
        motivo = row['motivo_perda']
        label = dict(MotivoPerda.choices).get(motivo, motivo)
        pct = round(row['qtd'] / total * 100, 1)
        itens.append({'motivo': motivo, 'label': label, 'qtd': row['qtd'], 'pct': pct})

    return {'total': total, 'itens': itens}
