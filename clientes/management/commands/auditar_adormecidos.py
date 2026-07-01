from django.core.management.base import BaseCommand

from clientes.services.categoria_automatica import auditar_adormecidos


class Command(BaseCommand):
    help = 'Lista clientes Ativos elegíveis para Adormecido (dry-run, não altera dados).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=None,
            help='Dias sem contato (padrão: ADORMECIMENTO_DIAS das settings).',
        )
        parser.add_argument(
            '--amostra',
            type=int,
            default=20,
            help='Quantidade de exemplos na listagem.',
        )

    def handle(self, *args, **options):
        rel = auditar_adormecidos(dias=options['dias'], amostra=options['amostra'])

        self.stdout.write(self.style.NOTICE('--- Auditoria Adormecido (dry-run) ---'))
        self.stdout.write(f'Dias sem contato: {rel["dias"]}')
        self.stdout.write(f'Limite: {rel["limite"]:%d/%m/%Y %H:%M}')
        self.stdout.write('')
        self.stdout.write('Clientes por categoria:')
        for cat, total in rel['por_categoria'].items():
            self.stdout.write(f'  {cat}: {total}')
        self.stdout.write('')
        self.stdout.write(
            self.style.WARNING(
                f'Ativos elegíveis para Adormecido: {rel["total_elegiveis"]}',
            ),
        )

        if rel['amostra']:
            self.stdout.write('')
            self.stdout.write('Amostra:')
            for item in rel['amostra']:
                self.stdout.write(
                    f'  - [{item["id"]}] {item["nome"]} ({item["vendedor"]}) — {item["motivo"]}',
                )
                if item['ultima_atividade']:
                    self.stdout.write(f'      última atividade: {item["ultima_atividade"]:%d/%m/%Y %H:%M}')
                if item['ultima_historico']:
                    self.stdout.write(f'      último histórico legado: {item["ultima_historico"]:%d/%m/%Y}')
                if not item['ultima_atividade'] and not item['ultima_historico']:
                    self.stdout.write(f'      cadastro no CRM: {item["created_at"]:%d/%m/%Y %H:%M}')

        if rel['total_elegiveis'] == 0:
            self.stdout.write('')
            self.stdout.write(
                'Nenhum Ativo elegível. Prospecção/Adormecido/Inativo não entram. '
                'Contato recente em Atividade Diária ou histórico legado impede a mudança.',
            )
