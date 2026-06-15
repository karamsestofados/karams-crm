from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.setup import invalidar_senha_admin
from comissoes.models import MetaMensal


class Command(BaseCommand):
    help = 'Invalida a senha do admin para definição manual após cada deploy'

    def handle(self, *args, **options):
        admin, created = invalidar_senha_admin()

        hoje = timezone.localdate()
        MetaMensal.objects.get_or_create(
            vendedor=None,
            mes=hoje.month,
            ano=hoje.year,
            defaults={'meta_contatos': 60, 'meta_vendas': 80000},
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Usuário "{admin.username}" criado. Defina a senha no primeiro acesso.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Senha de "{admin.username}" resetada. Defina novamente no acesso ao CRM.'
            ))
