from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


def _format_num_br(value, decimals=0):
    d = _to_decimal(value)
    if decimals == 0:
        quantized = int(d)
        int_part = f'{quantized:,}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return int_part
    quantized = d.quantize(Decimal(10) ** -decimals)
    s = f'{quantized:,.{decimals}f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


@register.filter(name='num_br')
def num_br(value, decimals=0):
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 0
    return _format_num_br(value, decimals)


@register.filter(name='brl_int')
def brl_int(value):
    return f'R$ {_format_num_br(value, 0)}'


@register.filter(name='brl')
def brl(value):
    return f'R$ {_format_num_br(value, 2)}'
