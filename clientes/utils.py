import re
from urllib.parse import urlparse


CEP_REGEX = re.compile(r'^\d{5}-\d{3}$')
TELEFONE_REGEX = re.compile(r'^\(\d{2}\) \d{4,5}-\d{4}$')


def normalizar_instagram(valor):
    if not valor:
        return ''
    valor = valor.strip()
    if not valor:
        return ''
    valor = valor.lstrip('@')
    if 'instagram.com' in valor.lower():
        if not valor.startswith(('http://', 'https://')):
            valor = f'https://{valor}'
        path = urlparse(valor).path.strip('/')
        if path:
            return path.split('/')[0].split('?')[0]
        return ''
    return valor.split('?')[0].split('/')[0]


def normalizar_telefone(valor):
    if not valor:
        return ''
    digitos = re.sub(r'\D', '', valor)
    if not digitos:
        return ''
    if len(digitos) == 11:
        return f'({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}'
    if len(digitos) == 10:
        return f'({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}'
    return valor.strip()


def normalizar_cep(valor):
    if not valor:
        return ''
    digitos = re.sub(r'\D', '', valor)
    if len(digitos) == 8:
        return f'{digitos[:5]}-{digitos[5:]}'
    return valor.strip()


def validar_cep(valor):
    if not valor:
        return True
    return bool(CEP_REGEX.match(valor))


def validar_telefone(valor):
    if not valor:
        return True
    return bool(TELEFONE_REGEX.match(valor))
