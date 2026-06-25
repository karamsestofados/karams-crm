from django.core.management.base import BaseCommand

from clientes.services.categoria_automatica import processar_clientes_adormecidos


class Command(BaseCommand):
    help = 'Move clientes Ativos sem contato há 30+ dias para Adormecido.'

    def handle(self, *args, **options):
        total = processar_clientes_adormecidos()
        self.stdout.write(self.style.SUCCESS(f'{total} cliente(s) movido(s) para Adormecido.'))
