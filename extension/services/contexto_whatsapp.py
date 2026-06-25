from collections import Counter
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente, StatusFunil, TipoInteracao
from comissoes.models import Venda
from extension.services.telefone import normalizar_chave_telefone, telefones_equivalentes
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado
from relacionamento.services.resumo_cliente import resumo_comercial_cliente

STATUS_ORCAMENTO_ABERTO = frozenset({
    StatusFunil.PROPOSTA_ENVIADA,
    StatusFunil.AGUARDANDO_RETORNO,
    StatusFunil.NEGOCIACAO,
})

ALERTA_SEM_COMPRA_DIAS = 45
ALERTA_SEM_CONTATO_DIAS = 30

_TEXTOS_GENERICOS_PRODUTO = frozenset({
    'pedido fechado',
    'pedido fechado.',
    'venda',
    'venda registrada',
    'sem produtos',
})


def _texto_produto_generico(texto: str) -> bool:
    if not texto or not str(texto).strip():
        return True
    normalizado = str(texto).strip().lower()
    return normalizado in _TEXTOS_GENERICOS_PRODUTO


def _nome_produtos_compra(registro) -> str | None:
    produtos = registro.get('produtos') or []
    if produtos:
        return ', '.join(produtos)
    texto = (registro.get('produtos_texto') or '').strip()
    if texto and not _texto_produto_generico(texto):
        return texto[:120]
    return None


def _referencia_compra(registro) -> str | None:
    venda_id = registro.get('venda_id')
    if venda_id:
        return f'Pedido #{venda_id}'
    return None


def buscar_cliente_por_telefone(usuario, telefone_raw):
    from extension.services.telefone import variantes_chave_telefone, variantes_telefones_crm

    chaves_busca = variantes_chave_telefone(telefone_raw)
    if not chaves_busca:
        return None

    candidatos = (
        Cliente.objects.para_usuario(usuario)
        .ativos()
        .exclude(telefone='')
        .select_related('vendedor')
        .order_by('pk')
    )
    for cliente in candidatos:
        if chaves_busca & variantes_telefones_crm(cliente.telefone):
            return cliente
    return None


def _compras_cliente(cliente):
    vendas = list(
        Venda.objects.filter(cliente=cliente)
        .prefetch_related('produtos')
        .order_by('-data', '-created_at')
    )
    legado = list(
        cliente.historico.filter(tipo=TipoInteracao.VENDA, valor__isnull=False)
        .prefetch_related('produtos')
        .order_by('-data', '-created_at')
    )
    registros = []
    for v in vendas:
        registros.append({
            'data': v.data,
            'valor': v.valor,
            'produtos': list(v.produtos.values_list('nome', flat=True)),
            'produtos_texto': v.produtos_texto or '',
            'venda_id': v.pk,
            'atividade_origem_id': v.atividade_origem_id,
            'created_at': v.created_at,
        })
    for h in legado:
        registros.append({
            'data': h.data,
            'valor': h.valor,
            'produtos': list(h.produtos.values_list('nome', flat=True)),
            'produtos_texto': h.observacao or '',
            'venda_id': None,
            'historico_id': h.pk,
            'created_at': getattr(h, 'created_at', None),
        })
    registros.sort(
        key=lambda r: (
            r['data'],
            r.get('created_at').timestamp() if r.get('created_at') else 0,
            r.get('venda_id') or r.get('historico_id') or 0,
        ),
        reverse=True,
    )
    return registros


def metricas_compra_cliente(cliente):
    compras = _compras_cliente(cliente)
    hoje = timezone.localdate()

    if not compras:
        return {
            'ultima_compra_valor': None,
            'ultima_compra_data': None,
            'dias_sem_comprar': None,
            'ticket_medio': None,
            'total_comprado': None,
            'produto_mais_comprado': None,
            'ultimo_produto_comprado': None,
            'ultima_compra_referencia': None,
        }

    valores = [c['valor'] for c in compras if c['valor'] is not None]
    ultima = compras[0]
    total = sum(valores, Decimal('0'))
    ticket = (total / len(valores)) if valores else None
    dias_sem = (hoje - ultima['data']).days if ultima.get('data') else None

    contador_produtos = Counter()
    for c in compras:
        if c['produtos']:
            contador_produtos.update(c['produtos'])
    produto_top = contador_produtos.most_common(1)[0][0] if contador_produtos else None

    return {
        'ultima_compra_valor': ultima['valor'],
        'ultima_compra_data': ultima['data'],
        'dias_sem_comprar': dias_sem,
        'ticket_medio': ticket,
        'total_comprado': total,
        'produto_mais_comprado': produto_top,
        'ultimo_produto_comprado': _nome_produtos_compra(ultima),
        'ultima_compra_referencia': _referencia_compra(ultima),
    }


def _contar_orcamentos_abertos(cliente):
    count = 0
    if cliente.status_funil in STATUS_ORCAMENTO_ABERTO:
        count += 1
    pendentes = (
        AtividadeCliente.objects.ativas()
        .filter(
            cliente=cliente,
            concluida=False,
            resultado__in=(Resultado.PROPOSTA_ENVIADA, Resultado.AGUARDANDO_RETORNO, Resultado.INTERESSADO),
        )
        .exclude(proxima_acao=ProximaAcao.SEM_ACAO)
        .count()
    )
    return max(count, pendentes)


def interacoes_resumo_cliente(cliente):
    resumo = resumo_comercial_cliente(cliente)
    ultima = resumo.get('ultima_atividade')
    return {
        'ultimo_contato_em': ultima.data_criacao if ultima else None,
        'dias_desde_ultimo_contato': cliente.dias_desde_ultimo_contato,
        'total_interacoes': resumo.get('total_interacoes', 0),
        'orcamentos_abertos': _contar_orcamentos_abertos(cliente),
    }


def alertas_cliente(cliente, usuario):
    alertas = []
    metricas = metricas_compra_cliente(cliente)
    interacoes = interacoes_resumo_cliente(cliente)
    hoje = timezone.localdate()

    dias_sem_comprar = metricas.get('dias_sem_comprar')
    if dias_sem_comprar is not None and dias_sem_comprar >= ALERTA_SEM_COMPRA_DIAS:
        alertas.append({
            'nivel': 'warning',
            'codigo': 'SEM_COMPRA_45D',
            'mensagem': f'Cliente há {dias_sem_comprar} dias sem comprar',
        })

    if interacoes['orcamentos_abertos'] > 0:
        n = interacoes['orcamentos_abertos']
        alertas.append({
            'nivel': 'info',
            'codigo': 'ORCAMENTO_PENDENTE',
            'mensagem': f'Possui {n} orçamento(s) em aberto',
        })

    dias_contato = interacoes.get('dias_desde_ultimo_contato')
    if dias_contato is not None and dias_contato >= ALERTA_SEM_CONTATO_DIAS:
        alertas.append({
            'nivel': 'warning',
            'codigo': 'SEM_CONTATO_30D',
            'mensagem': f'Sem contato registrado há {dias_contato} dias',
        })

    if cliente.categoria == CategoriaCliente.ADORMECIDO:
        alertas.append({
            'nivel': 'warning',
            'codigo': 'CLIENTE_ADORMECIDO',
            'mensagem': 'Cliente classificado como adormecido',
        })

    followup_atrasado = (
        AtividadeCliente.objects.ativas()
        .filter(
            cliente=cliente,
            concluida=False,
            data_proxima_acao__lt=hoje,
        )
        .exclude(proxima_acao=ProximaAcao.SEM_ACAO)
        .exists()
    )
    if followup_atrasado:
        alertas.append({
            'nivel': 'danger',
            'codigo': 'NEGOCIACAO_ATRASADA',
            'mensagem': 'Follow-up com data vencida',
        })

    if cliente.status_funil == StatusFunil.CLIENTE_PERDIDO:
        alertas.append({
            'nivel': 'danger',
            'codigo': 'CLIENTE_PERDIDO',
            'mensagem': 'Cliente marcado como perdido no funil',
        })

    return alertas


def _serializar_decimal(valor):
    if valor is None:
        return None
    return format(Decimal(valor).quantize(Decimal('0.01')), 'f')


def _url_crm_cliente(request, cliente_id):
    path = reverse('clientes:lista') + f'?id={cliente_id}&tab=historico'
    return request.build_absolute_uri(path)


def montar_contexto_extension(request, usuario, telefone_raw):
    if not telefone_raw or len(normalizar_chave_telefone(telefone_raw)) < 10:
        return {
            'encontrado': False,
            'mensagem': 'Número de telefone inválido ou incompleto.',
        }

    cliente = buscar_cliente_por_telefone(usuario, telefone_raw)
    if not cliente:
        return {
            'encontrado': False,
            'mensagem': 'Cliente não cadastrado com este telefone.',
        }

    metricas = metricas_compra_cliente(cliente)
    interacoes = interacoes_resumo_cliente(cliente)
    alertas = alertas_cliente(cliente, usuario)

    ultimo_contato = interacoes.get('ultimo_contato_em')
    vendedor = cliente.vendedor
    consultor_nome = ''
    if vendedor:
        consultor_nome = vendedor.get_full_name() or vendedor.username

    return {
        'encontrado': True,
        'cliente': {
            'id': cliente.pk,
            'nome': cliente.nome,
            'tipo_cliente_label': cliente.get_tipo_cliente_display() if cliente.tipo_cliente else '',
            'cidade': cliente.cidade or '',
            'estado': cliente.estado or '',
            'telefone': cliente.telefone or '',
            'categoria': cliente.categoria,
            'categoria_label': cliente.get_categoria_display(),
            'status_funil': cliente.status_funil,
            'status_funil_label': cliente.get_status_funil_display(),
            'consultor_nome': consultor_nome,
            'responsavel': cliente.responsavel or '',
            'url_crm': _url_crm_cliente(request, cliente.pk),
        },
        'metricas': {
            'ultima_compra_valor': _serializar_decimal(metricas['ultima_compra_valor']),
            'ultima_compra_data': (
                metricas['ultima_compra_data'].isoformat()
                if metricas['ultima_compra_data'] else None
            ),
            'dias_sem_comprar': metricas['dias_sem_comprar'],
            'ticket_medio': _serializar_decimal(metricas['ticket_medio']),
            'total_comprado': _serializar_decimal(metricas['total_comprado']),
            'produto_mais_comprado': metricas['produto_mais_comprado'],
            'ultimo_produto_comprado': metricas['ultimo_produto_comprado'],
            'ultima_compra_referencia': metricas['ultima_compra_referencia'],
        },
        'interacoes': {
            'ultimo_contato_em': ultimo_contato.isoformat() if ultimo_contato else None,
            'dias_desde_ultimo_contato': interacoes['dias_desde_ultimo_contato'],
            'total_interacoes': interacoes['total_interacoes'],
            'orcamentos_abertos': interacoes['orcamentos_abertos'],
        },
        'alertas': alertas,
    }
