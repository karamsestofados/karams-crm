from .models import TipoContato

TIMELINE_FILTROS = [
    ('', 'Todos'),
    (TipoContato.LIGACAO, 'Ligação'),
    (TipoContato.WHATSAPP, 'WhatsApp'),
    (TipoContato.EMAIL, 'E-mail'),
    (TipoContato.VISITA, 'Visita'),
    (TipoContato.NEGOCIACAO, 'Negociação'),
    (TipoContato.PROPOSTA, 'Proposta'),
    (TipoContato.POS_VENDA, 'Pós-venda'),
]
