from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from clientes.models import MotivoPerda, StatusFunil
from comissoes.models import Venda
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado

RESULTADO_PARA_FUNIL = {
    Resultado.PEDIDO_FECHADO: StatusFunil.PEDIDO_FECHADO,
    Resultado.PROPOSTA_ENVIADA: StatusFunil.PROPOSTA_ENVIADA,
    Resultado.SEM_INTERESSE: StatusFunil.CLIENTE_PERDIDO,
    Resultado.SEM_RESPOSTA: StatusFunil.EM_CONTATO,
    Resultado.CONTATO_REALIZADO: StatusFunil.EM_CONTATO,
    Resultado.PENDENTE: StatusFunil.EM_CONTATO,
    Resultado.INTERESSADO: StatusFunil.NEGOCIACAO,
    Resultado.AGUARDANDO_RETORNO: StatusFunil.AGUARDANDO_RETORNO,
    Resultado.POS_VENDA: StatusFunil.CLIENTE_ATIVO,
}


def _criar_venda(cliente, usuario, valor_venda, assunto='', resumo='', produto_relacionado=None, atividade=None):
    venda = Venda.objects.create(
        cliente=cliente,
        vendedor=usuario,
        data=timezone.localdate(),
        valor=valor_venda,
        produtos_texto=(assunto or resumo[:500]),
        atividade_origem=atividade,
    )
    if produto_relacionado:
        venda.produtos.add(produto_relacionado)
    return venda


def finalizar_atendimento(
    cliente, resultado, valor_venda=None, assunto='', resumo='',
    produto_relacionado=None, usuario=None, motivo_perda=None, motivo_perda_detalhe='',
    atividade=None,
):
    """Atualiza funil e dados do cliente quando o atendimento é encerrado."""
    hoje = timezone.localdate()
    update_fields = []

    if not cliente.data_primeiro_contato:
        cliente.data_primeiro_contato = hoje
        update_fields.append('data_primeiro_contato')

    novo_status = RESULTADO_PARA_FUNIL.get(resultado)
    if novo_status and cliente.status_funil != novo_status:
        cliente.status_funil = novo_status
        update_fields.append('status_funil')

    if resultado == Resultado.PEDIDO_FECHADO and cliente.status_funil == StatusFunil.PEDIDO_FECHADO:
        cliente.status_funil = StatusFunil.CLIENTE_ATIVO
        if 'status_funil' not in update_fields:
            update_fields.append('status_funil')

    if resultado == Resultado.SEM_INTERESSE and motivo_perda:
        cliente.motivo_perda = motivo_perda
        cliente.motivo_perda_detalhe = motivo_perda_detalhe or ''
        update_fields.extend(['motivo_perda', 'motivo_perda_detalhe'])

    if update_fields:
        cliente.save(update_fields=update_fields)

    if resultado == Resultado.PEDIDO_FECHADO and valor_venda and valor_venda > 0 and usuario:
        _criar_venda(cliente, usuario, valor_venda, assunto, resumo, produto_relacionado, atividade=atividade)


def registrar_interacao(
    cliente,
    usuario,
    tipo_contato,
    resumo,
    assunto='',
    resultado=Resultado.PENDENTE,
    humor_cliente=None,
    produto_relacionado=None,
    proxima_acao=ProximaAcao.SEM_ACAO,
    data_proxima_acao=None,
    hora_proxima_acao=None,
    valor_venda=None,
    motivo_perda=None,
    motivo_perda_detalhe='',
):
    if not resumo or not resumo.strip():
        raise ValidationError('O resumo é obrigatório.')

    if resultado == Resultado.SEM_INTERESSE and not motivo_perda:
        raise ValidationError('Informe o motivo da perda.')

    if proxima_acao != ProximaAcao.SEM_ACAO and not data_proxima_acao:
        raise ValidationError('Informe a data da próxima ação.')

    if proxima_acao == ProximaAcao.SEM_ACAO:
        data_proxima_acao = None
        hora_proxima_acao = None

    if resultado == Resultado.PEDIDO_FECHADO:
        if valor_venda is None or valor_venda <= 0:
            raise ValidationError('Informe o valor da venda para pedido fechado.')

    valor_atividade = None
    if valor_venda and valor_venda > 0:
        valor_atividade = valor_venda

    atividade = AtividadeCliente(
        cliente=cliente,
        usuario=usuario,
        tipo_contato=tipo_contato,
        assunto=assunto,
        resumo=resumo.strip(),
        resultado=resultado,
        humor_cliente=humor_cliente or None,
        produto_relacionado=produto_relacionado,
        proxima_acao=proxima_acao,
        data_proxima_acao=data_proxima_acao,
        hora_proxima_acao=hora_proxima_acao,
        concluida=proxima_acao == ProximaAcao.SEM_ACAO,
        valor_venda=valor_atividade,
    )
    atividade.full_clean()
    atividade.save()

    if proxima_acao == ProximaAcao.SEM_ACAO:
        finalizar_atendimento(
            cliente,
            resultado,
            valor_venda=valor_venda,
            assunto=assunto,
            resumo=resumo,
            produto_relacionado=produto_relacionado,
            usuario=usuario,
            motivo_perda=motivo_perda,
            motivo_perda_detalhe=motivo_perda_detalhe,
            atividade=atividade,
        )
    elif resultado == Resultado.PEDIDO_FECHADO and valor_venda and valor_venda > 0:
        _criar_venda(cliente, usuario, valor_venda, assunto, resumo, produto_relacionado, atividade=atividade)

    from comissoes.services.produtividade import avaliar_conquistas
    avaliar_conquistas(usuario)

    return atividade


def concluir_followup(
    atividade_pendente,
    usuario,
    resumo,
    tipo_contato=None,
    resultado=Resultado.PENDENTE,
    assunto='',
    humor_cliente=None,
    produto_relacionado=None,
    proxima_acao=ProximaAcao.SEM_ACAO,
    data_proxima_acao=None,
    hora_proxima_acao=None,
    valor_venda=None,
    motivo_perda=None,
    motivo_perda_detalhe='',
):
    if not atividade_pendente.tem_followup_pendente:
        raise ValidationError('Esta atividade não possui follow-up pendente.')

    if not resumo or not resumo.strip():
        raise ValidationError('Descreva o que aconteceu.')

    atividade_pendente.concluida = True
    atividade_pendente.save(update_fields=['concluida', 'data_atualizacao'])

    return registrar_interacao(
        cliente=atividade_pendente.cliente,
        usuario=usuario,
        tipo_contato=tipo_contato or atividade_pendente.tipo_contato,
        resumo=resumo.strip(),
        assunto=assunto or atividade_pendente.assunto,
        resultado=resultado,
        humor_cliente=humor_cliente,
        produto_relacionado=produto_relacionado or atividade_pendente.produto_relacionado,
        proxima_acao=proxima_acao,
        data_proxima_acao=data_proxima_acao,
        hora_proxima_acao=hora_proxima_acao,
        valor_venda=valor_venda,
        motivo_perda=motivo_perda,
        motivo_perda_detalhe=motivo_perda_detalhe,
    )
