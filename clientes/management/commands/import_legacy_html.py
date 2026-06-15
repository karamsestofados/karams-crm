from django.core.management.base import BaseCommand

from accounts.models import Papel, Usuario
from clientes.legacy_import import load_legacy_data, parse_date_br, split_modelos
from clientes.models import CategoriaCliente, Cliente, Produto
from comissoes.models import MetaMensal


CATEGORIA_MAP = {
    'ativos': CategoriaCliente.ATIVO,
    'adormecidos': CategoriaCliente.ADORMECIDO,
    'prospeccao': CategoriaCliente.PROSPECCAO,
}


class Command(BaseCommand):
    help = 'Importa clientes e produtos do HTML legado (DADOS_INICIAIS)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vendedor',
            type=str,
            default='vendedor',
            help='Username do vendedor responsável pelos clientes importados',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove clientes com legacy_id antes de importar',
        )

    def handle(self, *args, **options):
        vendedor = Usuario.objects.filter(username=options['vendedor']).first()
        if not vendedor:
            self.stderr.write(
                self.style.ERROR(
                    f'Vendedor "{options["vendedor"]}" não encontrado. '
                    'Execute seed_usuarios primeiro.'
                )
            )
            return

        if options['clear']:
            deleted, _ = Cliente.objects.filter(legacy_id__gt='').delete()
            self.stdout.write(f'Removidos {deleted} registros com legacy_id.')

        data = load_legacy_data()
        produtos_cache: dict[str, Produto] = {}
        criados = 0
        atualizados = 0

        for grupo, categoria in CATEGORIA_MAP.items():
            for item in data.get(grupo, []):
                legacy_id = item.get('id', '')
                nome = item.get('cliente', '').strip()
                if not nome:
                    continue

                telefone = item.get('telefone') or item.get('contato') or ''
                data_contato = parse_date_br(
                    item.get('data_contato') or item.get('data') or ''
                )

                cliente, created = Cliente.objects.update_or_create(
                    legacy_id=legacy_id,
                    defaults={
                        'vendedor': vendedor,
                        'categoria': categoria,
                        'nome': nome,
                        'cidade': item.get('cidade', '').strip(),
                        'estado': item.get('estado', '').strip()[:2],
                        'telefone': telefone.strip(),
                        'responsavel': item.get('responsavel', '').strip(),
                        'instagram': item.get('instagram', '').strip(),
                        'endereco': item.get('endereco', '').strip(),
                        'data_primeiro_contato': data_contato,
                        'feedback_original': item.get('feedback', '').strip(),
                        'ativo_no_sistema': True,
                    },
                )

                if created:
                    criados += 1
                else:
                    atualizados += 1

                nomes_produtos = split_modelos(item.get('modelos', ''))
                for novos in item.get('novosProdutos', []) or []:
                    nomes_produtos.extend(split_modelos(novos))

                produto_objs = []
                for nome_prod in nomes_produtos:
                    if nome_prod not in produtos_cache:
                        prod, _ = Produto.objects.get_or_create(nome=nome_prod)
                        produtos_cache[nome_prod] = prod
                    produto_objs.append(produtos_cache[nome_prod])

                if produto_objs:
                    cliente.produtos_exclusivos.set(produto_objs)

        self._ensure_meta_equipe()

        self.stdout.write(
            self.style.SUCCESS(
                f'Importação concluída: {criados} criados, {atualizados} atualizados, '
                f'{len(produtos_cache)} produtos.'
            )
        )

    def _ensure_meta_equipe(self):
        from django.utils import timezone
        hoje = timezone.localdate()
        MetaMensal.objects.get_or_create(
            vendedor=None,
            mes=hoje.month,
            ano=hoje.year,
            defaults={'meta_contatos': 60, 'meta_vendas': 80000},
        )
