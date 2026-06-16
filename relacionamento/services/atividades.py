from django.core.exceptions import ValidationError
from django.utils import timezone

from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado, TipoContato


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
):
    if not resumo or not resumo.strip():
        raise ValidationError('O resumo é obrigatório.')

    if proxima_acao != ProximaAcao.SEM_ACAO and not data_proxima_acao:
        raise ValidationError('Informe a data da próxima ação.')

    if proxima_acao == ProximaAcao.SEM_ACAO:
        data_proxima_acao = None
        hora_proxima_acao = None

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
    )
    atividade.full_clean()
    atividade.save()
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
    )
