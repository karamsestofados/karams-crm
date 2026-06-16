from relacionamento.models import ProximaAcao, TipoContato

from .event import CalendarEvent
from .google import build_google_calendar_url
from .policy import normalize_hora, should_open_calendar


def _label_proxima_acao(value):
    return dict(ProximaAcao.choices).get(value, value)


def _label_tipo_contato(value):
    return dict(TipoContato.choices).get(value, value)


def _build_location(cliente):
    if cliente.cidade:
        if cliente.estado:
            return f'{cliente.cidade}/{cliente.estado}'
        return cliente.cidade
    return ''


def _build_description(cliente, usuario, cleaned_data):
    produto = cleaned_data.get('produto_relacionado')
    produto_nome = produto.nome if produto else (cleaned_data.get('assunto') or '—')
    responsavel = usuario.get_full_name() or usuario.username
    lines = [
        'CRM Karams',
        '',
        f'Cliente: {cliente.nome}',
        f'Produto: {produto_nome}',
        f'Tipo de contato: {_label_tipo_contato(cleaned_data.get("tipo_contato", ""))}',
        '',
        'Resumo:',
        cleaned_data.get('resumo', '').strip(),
        '',
        'Responsável:',
        responsavel,
    ]
    return '\n'.join(lines)


def build_calendar_event_from_form(cliente, usuario, cleaned_data):
    proxima_acao = cleaned_data.get('proxima_acao')
    data = cleaned_data.get('data_proxima_acao')
    hora = normalize_hora(cleaned_data.get('hora_proxima_acao'))
    title = f'{_label_proxima_acao(proxima_acao)} - {cliente.nome}'
    return CalendarEvent(
        title=title,
        description=_build_description(cliente, usuario, cleaned_data),
        start_date=data,
        start_time=hora,
        location=_build_location(cliente),
    )


def resolve_calendar_url(cliente, usuario, cleaned_data):
    proxima_acao = cleaned_data.get('proxima_acao')
    data_proxima_acao = cleaned_data.get('data_proxima_acao')
    resultado = cleaned_data.get('resultado')
    if not should_open_calendar(proxima_acao, data_proxima_acao, resultado):
        return None
    event = build_calendar_event_from_form(cliente, usuario, cleaned_data)
    return build_google_calendar_url(event)
