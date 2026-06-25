import calendar
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db.models import Avg, Q, Sum
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from comissoes.models import ConquistaVendedor, MetaMensal, TipoConquista, Venda
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado, TipoContato

TIPOS_CONTATO_META = (
    TipoContato.LIGACAO,
    TipoContato.WHATSAPP,
    TipoContato.EMAIL,
    TipoContato.VISITA,
)

DIMENSOES = (
    ('giro_carteira', 'Giro de Carteira', 'meta_contatos', int),
    ('clientes_novos', 'Clientes Novos', 'meta_clientes_novos', int),
    ('propostas', 'Propostas / Orçamentos', 'meta_propostas', int),
    ('visitas', 'Visitas', 'meta_visitas', int),
    ('vendas_valor', 'Vendas', 'meta_vendas', Decimal),
)


def _meta_fallback(mes, ano):
    return MetaMensal(
        vendedor=None,
        mes=mes,
        ano=ano,
        meta_contatos=getattr(settings, 'METAS_PADRAO_CONTATOS', 60),
        meta_clientes_novos=0,
        meta_propostas=0,
        meta_visitas=0,
        meta_vendas=Decimal(str(getattr(settings, 'METAS_PADRAO_VENDAS', 80000))),
        ativo=True,
    )


def obter_meta(usuario, mes, ano):
    if usuario and not usuario.is_admin:
        meta = MetaMensal.objects.filter(
            vendedor=usuario, mes=mes, ano=ano, ativo=True,
        ).first()
        if meta:
            return meta
        meta_equipe = obter_meta_equipe(mes, ano)
        return meta_equipe

    if usuario and usuario.is_admin:
        return obter_meta_equipe(mes, ano)

    meta = MetaMensal.objects.filter(
        vendedor__isnull=True, mes=mes, ano=ano, ativo=True,
    ).first()
    return meta or _meta_fallback(mes, ano)


def somar_metas_vendedores(mes, ano):
    qs = MetaMensal.objects.filter(
        vendedor__isnull=False,
        vendedor__papel=Papel.VENDEDOR,
        vendedor__ativo=True,
        mes=mes,
        ano=ano,
        ativo=True,
    )
    if not qs.exists():
        return None
    agg = qs.aggregate(
        meta_contatos_avg=Avg('meta_contatos'),
        meta_clientes_novos=Sum('meta_clientes_novos'),
        meta_propostas=Sum('meta_propostas'),
        meta_visitas=Sum('meta_visitas'),
        meta_vendas=Sum('meta_vendas'),
    )
    meta_giro = min(100, round(agg.pop('meta_contatos_avg') or 0))
    return MetaMensal(
        vendedor=None,
        mes=mes,
        ano=ano,
        ativo=True,
        meta_contatos=meta_giro,
        **agg,
    )


def obter_meta_equipe(mes, ano):
    somada = somar_metas_vendedores(mes, ano)
    if somada:
        return somada
    manual = MetaMensal.objects.filter(
        vendedor__isnull=True, mes=mes, ano=ano, ativo=True,
    ).first()
    return manual or _meta_fallback(mes, ano)


def desempenho_equipe(mes, ano):
    from relacionamento.services.giro_carteira import calcular_giro_carteira

    meta = obter_meta_equipe(mes, ano)
    realizado = calcular_realizado(None, mes, ano)
    giro = calcular_giro_carteira(None, mes=mes, ano=ano)
    realizado['giro_carteira'] = giro['percentual']
    progresso = calcular_progresso(meta, realizado)
    return {
        'meta': meta,
        'realizado': realizado,
        'progresso': progresso,
        'pontuacao': pontuacao_geral(progresso),
        'giro_carteira': giro,
    }


def _periodo_mes(mes, ano):
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo_dia)


def _filtro_propostas_orcamentos():
    return (
        Q(resultado=Resultado.PROPOSTA_ENVIADA)
        | Q(tipo_contato__in=(TipoContato.PROPOSTA, TipoContato.NEGOCIACAO))
        | Q(resultado=Resultado.AGUARDANDO_RETORNO)
    )


def _aplicar_filtros_cliente(qs, filtros=None, prefix=''):
    if not filtros:
        return qs
    p = f'{prefix}__' if prefix else ''
    categoria = filtros.get('categoria')
    if categoria and categoria != 'todos':
        qs = qs.filter(**{f'{p}categoria': categoria})
    for field in (
        'tipo_cliente', 'modalidade_cliente', 'segmento',
        'origem_lead', 'status_funil', 'regiao_atuacao',
    ):
        val = filtros.get(field)
        if val and val != 'todos':
            qs = qs.filter(**{f'{p}{field}': val})
    estado = filtros.get('estado')
    if estado and estado != 'todos':
        qs = qs.filter(**{f'{p}estado__iexact': estado.upper()})
    if filtros.get('com_pedido_fechado') == '1':
        if prefix:
            qs = qs.filter(
                cliente__atividades__resultado=Resultado.PEDIDO_FECHADO,
                cliente__atividades__deleted_at__isnull=True,
            ).distinct()
        else:
            qs = qs.filter(
                atividades__resultado=Resultado.PEDIDO_FECHADO,
                atividades__deleted_at__isnull=True,
            ).distinct()
    return qs


def _atividades_base(
    usuario, mes=None, ano=None, de=None, ate=None,
    produto_id=None, regiao=None, filtros_cliente=None,
):
    qs = AtividadeCliente.objects.ativas().select_related('cliente', 'cliente__vendedor')
    if usuario:
        qs = qs.para_usuario(usuario)
    if de:
        qs = qs.filter(data_criacao__date__gte=de)
    if ate:
        qs = qs.filter(data_criacao__date__lte=ate)
    if mes and ano and not de and not ate:
        qs = qs.filter(data_criacao__month=mes, data_criacao__year=ano)
    if produto_id:
        qs = qs.filter(produto_relacionado_id=produto_id)
    if regiao:
        qs = qs.filter(cliente__regiao_atuacao=regiao)
    if filtros_cliente:
        qs = _aplicar_filtros_cliente(qs, filtros_cliente, prefix='cliente')
    return qs


def _clientes_base(
    usuario, mes=None, ano=None, de=None, ate=None,
    regiao=None, filtros_cliente=None,
):
    qs = Cliente.objects.para_usuario(usuario) if usuario else Cliente.objects.all()
    if de:
        qs = qs.filter(created_at__date__gte=de)
    if ate:
        qs = qs.filter(created_at__date__lte=ate)
    if mes and ano and not de and not ate:
        qs = qs.filter(created_at__month=mes, created_at__year=ano)
    if regiao:
        qs = qs.filter(regiao_atuacao=regiao)
    if filtros_cliente:
        qs = _aplicar_filtros_cliente(qs, filtros_cliente)
    return qs


def calcular_realizado(
    usuario, mes, ano, de=None, ate=None,
    produto_id=None, regiao=None, filtros_cliente=None,
):
    atividades = _atividades_base(
        usuario, mes, ano, de, ate, produto_id, regiao, filtros_cliente,
    )
    clientes = _clientes_base(
        usuario, mes, ano, de, ate, regiao, filtros_cliente,
    )

    contatos = atividades.filter(tipo_contato__in=TIPOS_CONTATO_META).count()
    clientes_novos = clientes.count()
    propostas = atividades.filter(_filtro_propostas_orcamentos()).count()
    visitas = atividades.filter(tipo_contato=TipoContato.VISITA).count()

    vendas_qs = Venda.objects.filter(vendedor=usuario) if usuario else Venda.objects.all()
    if de:
        vendas_qs = vendas_qs.filter(data__gte=de)
    if ate:
        vendas_qs = vendas_qs.filter(data__lte=ate)
    if mes and ano and not de and not ate:
        vendas_qs = vendas_qs.filter(data__month=mes, data__year=ano)

    vendas_valor = vendas_qs.aggregate(total=Sum('valor'))['total'] or Decimal('0')

    return {
        'contatos': contatos,
        'clientes_novos': clientes_novos,
        'propostas': propostas,
        'visitas': visitas,
        'vendas_valor': vendas_valor,
        'total_interacoes': atividades.count(),
    }


def _status_meta(percentual):
    if percentual is None:
        return ''
    if percentual >= 120:
        return 'superada'
    if percentual >= 100:
        return 'atingida'
    return ''


def _percentual(realizado, meta, is_decimal=False):
    if is_decimal:
        meta_val = float(meta or 0)
        real_val = float(realizado or 0)
    else:
        meta_val = float(meta or 0)
        real_val = float(realizado or 0)
    if meta_val <= 0:
        return None
    return min(round(real_val / meta_val * 100, 1), 999)


def calcular_progresso(meta, realizado):
    itens = []
    for key, label, meta_field, tipo in DIMENSOES:
        meta_val = getattr(meta, meta_field, 0)
        real_val = realizado.get(key, 0)
        is_decimal = tipo is Decimal
        pct = _percentual(real_val, meta_val, is_decimal)
        itens.append({
            'key': key,
            'label': label,
            'meta': meta_val,
            'realizado': real_val,
            'percentual': pct,
            'percentual_display': f'{pct}%' if pct is not None else '—',
            'status': _status_meta(pct),
            'is_moeda': is_decimal,
        })
    return itens


def pontuacao_geral(progresso):
    pcts = [p['percentual'] for p in progresso if p['percentual'] is not None]
    if not pcts:
        return 0
    capped = [min(p, 100) for p in pcts]
    return round(sum(capped) / len(capped), 1)


def desempenho_usuario(usuario, mes, ano):
    from relacionamento.services.giro_carteira import calcular_giro_carteira

    meta = obter_meta(usuario, mes, ano)
    realizado = calcular_realizado(usuario, mes, ano)
    giro = calcular_giro_carteira(usuario, mes=mes, ano=ano)
    realizado['giro_carteira'] = giro['percentual']
    progresso = calcular_progresso(meta, realizado)
    return {
        'usuario': usuario,
        'meta': meta,
        'realizado': realizado,
        'progresso': progresso,
        'pontuacao': pontuacao_geral(progresso),
        'giro_carteira': giro,
    }


def falta_para_meta_vendas(meta_vendas, realizado_vendas):
    meta_val = float(meta_vendas or 0)
    real_val = float(realizado_vendas or 0)
    falta = max(0, meta_val - real_val)
    return {
        'falta': Decimal(str(round(falta, 2))),
        'atingida': falta <= 0,
    }


def meta_do_dia(usuario, data=None):
    data = data or timezone.localdate()
    meta = obter_meta(usuario, data.month, data.year)
    meta_contatos = meta.meta_dia_contatos
    realizado = (
        AtividadeCliente.objects.ativas()
        .para_usuario(usuario)
        .filter(data_criacao__date=data, tipo_contato__in=TIPOS_CONTATO_META)
        .count()
    )
    pct = _percentual(realizado, meta_contatos)
    return {
        'meta_contatos': meta_contatos,
        'realizado_contatos': realizado,
        'percentual': pct,
        'percentual_display': f'{pct}%' if pct is not None else '—',
        'status': _status_meta(pct),
        'data': data,
    }


def ranking_mensal(mes, ano, limit=None):
    vendedores = Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True).order_by('first_name')
    ranking = []
    for v in vendedores:
        desemp = desempenho_usuario(v, mes, ano)
        if desemp['pontuacao'] > 0 or any(
            p['realizado'] for p in desemp['progresso']
        ):
            ranking.append(desemp)
    ranking.sort(key=lambda x: x['pontuacao'], reverse=True)
    for i, item in enumerate(ranking, start=1):
        item['posicao'] = i
    if limit:
        return ranking[:limit]
    return ranking


def conversao_orcamentos(
    usuario, de, ate, produto_id=None, regiao=None, filtros_cliente=None,
):
    atividades = _atividades_base(
        usuario, de=de, ate=ate,
        produto_id=produto_id, regiao=regiao, filtros_cliente=filtros_cliente,
    )
    enviados = atividades.filter(_filtro_propostas_orcamentos()).count()
    fechados = atividades.filter(resultado=Resultado.PEDIDO_FECHADO).count()
    if enviados == 0:
        return {'enviados': 0, 'fechados': fechados, 'taxa_pct': 0}
    taxa = min(100, round(fechados / enviados * 100, 1))
    return {'enviados': enviados, 'fechados': fechados, 'taxa_pct': taxa}


def taxa_conversao(usuario, de, ate, regiao=None, filtros_cliente=None):
    prospectados_qs = _clientes_base(
        usuario, de=de, ate=ate, regiao=regiao, filtros_cliente=filtros_cliente,
    )
    prospectados_ids = list(prospectados_qs.values_list('pk', flat=True))
    prospectados = len(prospectados_ids)
    if prospectados == 0:
        return {'prospectados': 0, 'convertidos': 0, 'taxa_pct': 0}

    convertidos_ids = set(
        AtividadeCliente.objects.ativas()
        .filter(
            cliente_id__in=prospectados_ids,
            resultado=Resultado.PEDIDO_FECHADO,
            data_criacao__date__gte=de,
            data_criacao__date__lte=ate,
        )
        .values_list('cliente_id', flat=True)
    )
    vendas_qs = Venda.objects.filter(
        cliente_id__in=prospectados_ids,
        data__gte=de,
        data__lte=ate,
    )
    if usuario:
        vendas_qs = vendas_qs.filter(vendedor=usuario)
    vendas_ids = set(vendas_qs.values_list('cliente_id', flat=True))
    convertidos = len(convertidos_ids | vendas_ids)
    taxa = round(convertidos / prospectados * 100, 1)
    return {'prospectados': prospectados, 'convertidos': convertidos, 'taxa_pct': taxa}


def equipe_comercial(mes, ano):
    return ranking_mensal(mes, ano)


def _conceder_conquista(usuario, tipo, mes=None, ano=None):
    ConquistaVendedor.objects.get_or_create(
        usuario=usuario,
        tipo=tipo,
        mes=mes,
        ano=ano,
        defaults={},
    )


def total_contatos_historico(usuario):
    return (
        AtividadeCliente.objects.ativas()
        .para_usuario(usuario)
        .filter(tipo_contato__in=TIPOS_CONTATO_META)
        .count()
    )


def avaliar_conquistas(usuario, mes=None, ano=None):
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year

    if Venda.objects.filter(vendedor=usuario).exists():
        _conceder_conquista(usuario, TipoConquista.PRIMEIRA_VENDA)
    elif AtividadeCliente.objects.ativas().filter(
        usuario=usuario, resultado=Resultado.PEDIDO_FECHADO,
    ).exists():
        _conceder_conquista(usuario, TipoConquista.PRIMEIRA_VENDA)

    if total_contatos_historico(usuario) >= 100:
        _conceder_conquista(usuario, TipoConquista.CEM_CONTATOS)

    desemp = desempenho_usuario(usuario, mes, ano)
    if desemp['pontuacao'] >= 100:
        _conceder_conquista(usuario, TipoConquista.META_BATIDA, mes=mes, ano=ano)

    ranking = ranking_mensal(mes, ano)
    if ranking and ranking[0]['usuario'].pk == usuario.pk:
        _conceder_conquista(usuario, TipoConquista.TOP_MES, mes=mes, ano=ano)

    mes_ant = mes - 1 if mes > 1 else 12
    ano_ant = ano if mes > 1 else ano - 1
    desemp_ant = desempenho_usuario(usuario, mes_ant, ano_ant)
    crescimento = desemp['pontuacao'] - desemp_ant['pontuacao']
    if crescimento > 0:
        todos = ranking_mensal(mes, ano)
        crescimentos = []
        for item in todos:
            u = item['usuario']
            ant = desempenho_usuario(u, mes_ant, ano_ant)
            crescimentos.append((u, item['pontuacao'] - ant['pontuacao']))
        crescimentos.sort(key=lambda x: x[1], reverse=True)
        if crescimentos and crescimentos[0][0].pk == usuario.pk and crescimentos[0][1] > 0:
            _conceder_conquista(usuario, TipoConquista.MAIOR_CRESCIMENTO, mes=mes, ano=ano)

    _avaliar_conquistas_mensais_extras(usuario, mes, ano)


def _avaliar_conquistas_mensais_extras(usuario, mes, ano):
    from datetime import timedelta

    inicio = date(ano, mes, 1)
    ultimo = calendar.monthrange(ano, mes)[1]
    fim = date(ano, mes, ultimo)

    whatsapp_count = (
        AtividadeCliente.objects.ativas()
        .filter(
            usuario=usuario,
            tipo_contato=TipoContato.WHATSAPP,
            data_criacao__date__gte=inicio,
            data_criacao__date__lte=fim,
        )
        .count()
    )
    followups = (
        AtividadeCliente.objects.ativas()
        .filter(
            usuario=usuario,
            concluida=True,
            data_criacao__date__gte=inicio,
            data_criacao__date__lte=fim,
        )
        .exclude(proxima_acao=ProximaAcao.SEM_ACAO)
        .count()
    )

    vendedores = list(Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True))
    if vendedores:
        whatsapp_rank = sorted(
            vendedores,
            key=lambda u: AtividadeCliente.objects.ativas().filter(
                usuario=u, tipo_contato=TipoContato.WHATSAPP,
                data_criacao__date__gte=inicio, data_criacao__date__lte=fim,
            ).count(),
            reverse=True,
        )
        if whatsapp_rank and whatsapp_rank[0].pk == usuario.pk and whatsapp_count > 0:
            _conceder_conquista(usuario, TipoConquista.REI_WHATSAPP, mes=mes, ano=ano)

        follow_rank = sorted(
            vendedores,
            key=lambda u: AtividadeCliente.objects.ativas().filter(
                usuario=u, concluida=True,
                data_criacao__date__gte=inicio, data_criacao__date__lte=fim,
            ).exclude(proxima_acao=ProximaAcao.SEM_ACAO).count(),
            reverse=True,
        )
        if follow_rank and follow_rank[0].pk == usuario.pk and followups > 0:
            _conceder_conquista(usuario, TipoConquista.MESTRE_FOLLOWUP, mes=mes, ano=ano)

    streak = 0
    dia = timezone.localdate()
    while streak < 7:
        meta = meta_do_dia(usuario, dia)
        if meta['realizado_contatos'] >= meta['meta_contatos']:
            streak += 1
        else:
            break
        dia -= timedelta(days=1)
    if streak >= 7:
        _conceder_conquista(usuario, TipoConquista.STREAK_META_7, mes=mes, ano=ano)


def avaliar_conquistas_equipe(mes=None, ano=None):
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year
    for v in Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True):
        avaliar_conquistas(v, mes, ano)
