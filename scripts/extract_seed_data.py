"""Extrai DADOS_INICIAIS do HTML legado e gera JSON para importação."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'karams_crm.settings.development')

import django
django.setup()

from clientes.legacy_import import load_legacy_data, save_seed_json


def main():
    html_path = BASE_DIR / 'karams crm (8).html'
    if not html_path.exists():
        print(f'Arquivo não encontrado: {html_path}', file=sys.stderr)
        sys.exit(1)

    data = load_legacy_data()
    output = save_seed_json()
    print(f'Seed extraído: {output}')
    print(f'  ativos: {len(data.get("ativos", []))}')
    print(f'  adormecidos: {len(data.get("adormecidos", []))}')
    print(f'  prospeccao: {len(data.get("prospeccao", []))}')


if __name__ == '__main__':
    main()
