"""Utilitários para importação de dados legados."""

import json
import re
from datetime import datetime
from pathlib import Path

from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)
HTML_PATH = BASE_DIR / 'karams crm (8).html'
SEED_JSON = BASE_DIR / 'clientes' / 'fixtures' / 'legacy_seed.json'

CATEGORIAS = ('ativos', 'adormecidos', 'prospeccao')
FIELD_PATTERN = re.compile(r"(\w+):'((?:[^'\\]|\\.)*)'")


def parse_date_br(value: str):
    if not value or not value.strip():
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_produto_nome(raw: str) -> str:
    return raw.strip().upper()


def split_modelos(modelos_str: str) -> list[str]:
    if not modelos_str:
        return []
    parts = re.split(r'[-–—,/\s]+', modelos_str.upper())
    cleaned = []
    for part in parts:
        part = part.strip()
        if not part or len(part) < 2:
            continue
        if part.startswith('POL.') or part.startswith('PO.'):
            part = part.replace('.', ' ').strip()
        cleaned.append(normalize_produto_nome(part))
    return list(dict.fromkeys(cleaned))


def _parse_record_line(line: str) -> dict | None:
    line = line.strip().rstrip(',')
    if not line.startswith('{id:'):
        return None
    record = {}
    for match in FIELD_PATTERN.finditer(line):
        record[match.group(1)] = match.group(2)
    return record if record.get('id') else None


def parse_html_dados_iniciais(html: str) -> dict:
    result = {cat: [] for cat in CATEGORIAS}
    current = None

    for line in html.splitlines():
        stripped = line.strip()
        for cat in CATEGORIAS:
            if stripped.startswith(f'{cat}:') or stripped == f'{cat}: [':
                current = cat
                break
        if stripped.startswith('},') or stripped == '},':
            current = None
        if stripped.startswith('],'):
            current = None

        if current and stripped.startswith('{id:'):
            record = _parse_record_line(stripped)
            if record:
                result[current].append(record)

    return result


def load_legacy_data(force_html: bool = False) -> dict:
    if SEED_JSON.exists() and not force_html:
        data = json.loads(SEED_JSON.read_text(encoding='utf-8'))
        if any(data.get(cat) for cat in CATEGORIAS):
            return data

    if not HTML_PATH.exists():
        raise FileNotFoundError(f'HTML legado não encontrado: {HTML_PATH}')

    html = HTML_PATH.read_text(encoding='utf-8')
    return parse_html_dados_iniciais(html)


def save_seed_json(force_html: bool = True) -> Path:
    data = load_legacy_data(force_html=force_html)
    SEED_JSON.parent.mkdir(parents=True, exist_ok=True)
    SEED_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return SEED_JSON
