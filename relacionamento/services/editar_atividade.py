from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError

from comissoes.models import Venda
from relacionamento.models import (
    AtividadeCliente,
    AtividadeClienteEdicao,
    HumorCliente,
    ProximaAcao,
    Resultado,
    TipoContato,
)

CAMPOS_EDITAVEIS = (
    ('tipo_contato', 'TIPO DE CONTATO'),
    ('assunto', 'ASSUNTO'),
    ('resumo', 'OBSERVAÇÃO'),
    ('resultado', 'RESULTADO'),
    ('humor_cliente', 'HUMOR'),
    ('valor_venda', 'VENDA'),
    ('proxima_acao', 'PRÓXIMA AÇÃO'),
    ('data_proxima_acao', 'DATA PRÓXIMA AÇÃO'),
    ('hora_proxima_acao', 'HORA PRÓXIMA AÇÃO'),
)


def _formatar_valor(campo, valor):
    if valor is None or valor == '':
        return '—'
    if campo == 'tipo_contato':
        return dict(TipoContato.choices).get(valor, str(valor))
    if campo == 'resultado':
        return dict(Resultado.choices).get(valor, str(valor))
    if campo == 'humor_cliente':
        return dict(HumorCliente.choices).get(valor, str(valor))
    if campo == 'proxima_acao':
        return dict(ProximaAcao.choices).get(valor, str(valor))
    if campo == 'valor_venda':
        return f'R$ {Decimal(valor):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    if campo == 'data_proxima_acao':
        return valor.strftime('%d/%m/%Y')
    if campo == 'hora_proxima_acao':
        return valor.strftime('%H:%M')
    return str(valor)


def _formatar_produtos(produtos):
    if not produtos:
        return '—'
    nomes = sorted(p.nome for p in produtos)
    return ', '.join(nomes) if nomes else '—'


def _valor_campo(atividade, campo):
    return getattr(atividade, campo)


def _aplicar_campo(atividade, campo, valor):
    setattr(atividade, campo, valor)


def pode_editar_atividade(atividade, usuario):
    if not atividade.deleted_at:
        return atividade.pode_editar(usuario)
    return False


def _sincronizar_venda(atividade, valor_anterior):
    if atividade.resultado != Resultado.PEDIDO_FECHADO:
        return
    venda = Venda.objects.filter(atividade_origem=atividade).first()
    if not venda and valor_anterior is not None:
        venda = (
            Venda.objects.filter(
                cliente=atividade.cliente,
                data=atividade.data_criacao.date(),
                valor=valor_anterior,
            )
            .order_by('-created_at')
            .first()
        )
        if venda and not venda.atividade_origem_id:
            venda.atividade_origem = atividade
            venda.save(update_fields=['atividade_origem'])
    if venda and atividade.valor_venda:
        venda.valor = atividade.valor_venda
        venda.save(update_fields=['valor'])


def editar_atividade(atividade, usuario, dados):
    if not pode_editar_atividade(atividade, usuario):
        raise PermissionDenied('Você não pode editar este registro.')

    # ModelForm atualiza a instância em memória durante is_valid(); recarregar do banco
    # garante comparação correta entre valores antigos e novos.
    atividade = (
        AtividadeCliente.objects
        .prefetch_related('produtos_relacionados')
        .get(pk=atividade.pk)
    )

    alteracoes = []
    valor_anterior_venda = atividade.valor_venda
    dados = dict(dados)

    novos_produtos = dados.pop('produtos_relacionados', None)
    if novos_produtos is not None:
        novos_produtos = list(novos_produtos)
        antigos_produtos = list(atividade.produtos_relacionados.all())
        antigos_ids = {p.pk for p in antigos_produtos}
        novos_ids = {p.pk for p in novos_produtos}
        if antigos_ids != novos_ids:
            alteracoes.append({
                'campo': 'produtos_relacionados',
                'label': 'PRODUTO',
                'antes': _formatar_produtos(antigos_produtos),
                'depois': _formatar_produtos(novos_produtos),
            })

    for campo, label in CAMPOS_EDITAVEIS:
        if campo not in dados:
            continue
        novo = dados[campo]
        antigo = _valor_campo(atividade, campo)
        if antigo == novo:
            continue
        if campo == 'valor_venda':
            antigo_cmp = Decimal(antigo or 0)
            novo_cmp = Decimal(novo or 0) if novo is not None else Decimal('0')
            if antigo_cmp == novo_cmp:
                continue
        alteracoes.append({
            'campo': campo,
            'label': label,
            'antes': _formatar_valor(campo, antigo),
            'depois': _formatar_valor(campo, novo),
        })
        _aplicar_campo(atividade, campo, novo)

    if not alteracoes:
        return None

    if atividade.resultado == Resultado.PEDIDO_FECHADO:
        if atividade.valor_venda is None or atividade.valor_venda <= 0:
            raise ValidationError('Informe o valor da venda para pedido fechado.')

    if atividade.proxima_acao != ProximaAcao.SEM_ACAO and not atividade.data_proxima_acao:
        raise ValidationError('Informe a data da próxima ação.')

    if atividade.proxima_acao == ProximaAcao.SEM_ACAO:
        atividade.data_proxima_acao = None
        atividade.hora_proxima_acao = None
        atividade.concluida = True
    else:
        atividade.concluida = False

    atividade.full_clean()
    atividade.save()

    if novos_produtos is not None:
        atividade.produtos_relacionados.set(novos_produtos)

    if any(a['campo'] == 'valor_venda' for a in alteracoes):
        _sincronizar_venda(atividade, valor_anterior_venda)

    edicao = AtividadeClienteEdicao.objects.create(
        atividade=atividade,
        usuario=usuario,
        alteracoes=alteracoes,
    )
    return edicao
