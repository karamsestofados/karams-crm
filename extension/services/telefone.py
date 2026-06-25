import re

SEPARADORES_TELEFONE_CRM = re.compile(r'[/;,|]+')


def extrair_digitos(valor) -> str:
    return re.sub(r'\D', '', valor or '')


def extrair_partes_telefone_crm(campo) -> list[str]:
    """Separa um ou mais telefones armazenados no campo CRM."""
    if not campo:
        return []
    partes = [p.strip() for p in SEPARADORES_TELEFONE_CRM.split(str(campo)) if p.strip()]
    return partes or [str(campo).strip()]


def _remover_ddi(digitos: str) -> str:
    if digitos.startswith('55') and len(digitos) >= 12:
        return digitos[2:]
    return digitos


def _inserir_nono_digito_celular(local: str) -> str | None:
    """DDD (2) + 8 dígitos (9XXXXXXX) → insere 9 após DDD."""
    if len(local) != 10:
        return None
    ddd, resto = local[:2], local[2:]
    if len(resto) == 8 and resto[0] == '9':
        return f'{ddd}9{resto}'
    return None


def _remover_nono_digito_celular(local: str) -> str | None:
    """DDD (2) + 9 + 8 dígitos → remove 9 extra após DDD."""
    if len(local) != 11:
        return None
    ddd, resto = local[:2], local[2:]
    if len(resto) == 9 and resto[0] == '9':
        return f'{ddd}{resto[1:]}'
    return None


def variantes_chave_telefone(valor) -> set[str]:
    """Gera chaves comparáveis incluindo migração do nono dígito celular BR."""
    digitos = extrair_digitos(valor)
    if not digitos:
        return set()

    chaves = set()
    local = _remover_ddi(digitos)

    if len(local) >= 11:
        chaves.add(local[-11:])
    if len(local) >= 10:
        chaves.add(local[-10:])

    com_nono = _inserir_nono_digito_celular(local)
    if com_nono:
        chaves.add(com_nono)
        chaves.add(com_nono[-10:])

    sem_nono = _remover_nono_digito_celular(local)
    if sem_nono:
        chaves.add(sem_nono)
        chaves.add(sem_nono[-10:])

    return {c for c in chaves if len(c) >= 10}


def variantes_telefones_crm(campo) -> set[str]:
    """Variantes comparáveis para todos os telefones de um campo CRM."""
    chaves: set[str] = set()
    for parte in extrair_partes_telefone_crm(campo):
        chaves |= variantes_chave_telefone(parte)
    return chaves


def normalizar_chave_telefone(valor) -> str:
    """Retorna sufixo comparável (10 ou 11 dígitos locais, sem DDI 55)."""
    variantes = variantes_chave_telefone(valor)
    if not variantes:
        return ''
    return max(variantes, key=len)


def telefones_equivalentes(a, b) -> bool:
    ka = variantes_chave_telefone(a)
    kb = variantes_chave_telefone(b)
    if not ka or not kb:
        return False
    if ka & kb:
        return True
    for a_key in ka:
        for b_key in kb:
            if len(a_key) >= 10 and len(b_key) >= 10 and a_key[-10:] == b_key[-10:]:
                return True
    return False
