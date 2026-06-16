from datetime import time

from relacionamento.models import ProximaAcao, Resultado

HORA_PADRAO_FOLLOWUP = time(9, 0)

PROXIMAS_ACOES_CALENDAR = frozenset({
    ProximaAcao.LIGAR,
    ProximaAcao.ENVIAR_CATALOGO,
    ProximaAcao.ENVIAR_PROPOSTA,
    ProximaAcao.AGENDAR_VISITA,
    ProximaAcao.ENVIAR_WHATSAPP,
    ProximaAcao.ENVIAR_EMAIL,
})

RESULTADOS_BLOQUEIAM_CALENDAR = frozenset({
    Resultado.SEM_INTERESSE,
    Resultado.PEDIDO_FECHADO,
})

RESULTADOS_EXIGEM_FOLLOWUP = frozenset({
    Resultado.AGUARDANDO_RETORNO,
    Resultado.PROPOSTA_ENVIADA,
    Resultado.INTERESSADO,
})

MSG_FOLLOWUP_OBRIGATORIO = (
    'É obrigatório agendar um próximo contato para negociações em andamento.'
)


def normalize_hora(hora):
    if hora is None:
        return HORA_PADRAO_FOLLOWUP
    return hora


def should_open_calendar(proxima_acao, data_proxima_acao, resultado):
    if not data_proxima_acao:
        return False
    if proxima_acao == ProximaAcao.SEM_ACAO:
        return False
    if proxima_acao not in PROXIMAS_ACOES_CALENDAR:
        return False
    if resultado in RESULTADOS_BLOQUEIAM_CALENDAR:
        return False
    return True


def exige_followup(resultado):
    return resultado in RESULTADOS_EXIGEM_FOLLOWUP


def validar_followup_obrigatorio(resultado, proxima_acao, data_proxima_acao):
    if not exige_followup(resultado):
        return None
    if proxima_acao == ProximaAcao.SEM_ACAO or not data_proxima_acao:
        return MSG_FOLLOWUP_OBRIGATORIO
    return None
