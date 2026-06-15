from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Papel, Usuario
from comissoes.models import MetaMensal


class Command(BaseCommand):
    help = 'Cria usuário vendedor demo e metas (admin via /accounts/configuracao-inicial/)'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Atualiza senha do vendedor se existir')
        parser.add_argument(
            '--com-admin',
            action='store_true',
            help='Cria admin com senha demo (apenas desenvolvimento local)',
        )

    def handle(self, *args, **options):
        hoje = timezone.localdate()

        if options['com_admin']:
            self._criar_admin_demo()

        vendedor, created = Usuario.objects.get_or_create(
            username='vendedor',
            defaults={
                'email': 'vendedor@karams.com.br',
                'first_name': 'Vendedora',
                'last_name': 'Karams',
                'papel': Papel.VENDEDOR,
                'is_staff': False,
                'is_superuser': False,
            },
        )
        if created or options['force']:
            vendedor.set_password('vendedor123')
            vendedor.papel = Papel.VENDEDOR
            vendedor.save()
            status = 'criado' if created else 'atualizado'
            self.stdout.write(self.style.SUCCESS(f'Vendedor {vendedor.username} {status}.'))
        else:
            self.stdout.write(f'Vendedor {vendedor.username} já existe (use --force para resetar).')

        MetaMensal.objects.get_or_create(
            vendedor=None,
            mes=hoje.month,
            ano=hoje.year,
            defaults={'meta_contatos': 60, 'meta_vendas': 80000},
        )
        self.stdout.write(self.style.SUCCESS('Metas da equipe configuradas (se ainda não existirem).'))

    def _criar_admin_demo(self):
        admin, created = Usuario.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@karams.com.br',
                'first_name': 'Admin',
                'last_name': 'Karams',
                'papel': Papel.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.set_password('admin123')
        admin.papel = Papel.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        status = 'criado' if created else 'atualizado'
        self.stdout.write(self.style.WARNING(f'Admin demo {status} (admin / admin123). Use só em dev local.'))
