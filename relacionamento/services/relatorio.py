from django.db.models import Count, Q

from accounts.models import Papel, Usuario
from relacionamento.models import AtividadeCliente, Resultado, TipoContato


def filtrar_atividades(request):
    qs = AtividadeCliente.objects.ativas().select_related(
        'cliente', 'usuario', 'cliente__vendedor',
    ).prefetch_related('produtos_relacionados')

    if not request.user.is_admin:
        qs = qs.filter(cliente__vendedor=request.user)

    data_de = request.GET.get('de')
    data_ate = request.GET.get('ate')
    if data_de:
        qs = qs.filter(data_criacao__date__gte=data_de)
    if data_ate:
        qs = qs.filter(data_criacao__date__lte=data_ate)

    vendedor_id = request.GET.get('vendedor')
    if vendedor_id and request.user.is_admin:
        qs = qs.filter(cliente__vendedor_id=vendedor_id)

    cliente_id = request.GET.get('cliente')
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)

    produto_id = request.GET.get('produto')
    if produto_id:
        qs = qs.filter(produtos_relacionados__id=produto_id).distinct()

    tipo = request.GET.get('tipo_contato')
    if tipo and tipo != 'todos':
        qs = qs.filter(tipo_contato=tipo)

    return qs


def indicadores_por_tipo(qs):
    mapping = {
        'ligacoes': TipoContato.LIGACAO,
        'whatsapps': TipoContato.WHATSAPP,
        'emails': TipoContato.EMAIL,
        'visitas': TipoContato.VISITA,
        'reunioes': TipoContato.REUNIAO,
        'propostas': TipoContato.PROPOSTA,
    }
    counts = {k: qs.filter(tipo_contato=v).count() for k, v in mapping.items()}
    counts['pedidos_fechados'] = qs.filter(resultado=Resultado.PEDIDO_FECHADO).count()
    return counts


def ranking_vendedores(qs):
    if not qs.exists():
        return []

    vendedores = Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True)
    ranking = []
    for v in vendedores:
        v_qs = qs.filter(cliente__vendedor=v)
        total = v_qs.count()
        if total == 0:
            continue
        ranking.append({
            'vendedor': v,
            'interacoes': total,
            'clientes_atendidos': v_qs.values('cliente_id').distinct().count(),
            'propostas': v_qs.filter(
                Q(tipo_contato=TipoContato.PROPOSTA)
                | Q(resultado=Resultado.PROPOSTA_ENVIADA)
            ).count(),
            'fechamentos': v_qs.filter(resultado=Resultado.PEDIDO_FECHADO).count(),
        })
    ranking.sort(key=lambda x: x['interacoes'], reverse=True)
    return ranking
