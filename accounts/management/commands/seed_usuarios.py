from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Papel, Usuario
from comissoes.models import MetaMensal


class Command(BaseCommand):
    help = 'Cria usuários demo: admin + vendedor'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Atualiza senhas se usuários existirem')

    def handle(self, *args, **options):
        hoje = timezone.localdate()
        usuarios = [
            {
                'username': 'admin',
                'password': 'admin123',
                'email': 'admin@karams.com.br',
                'first_name': 'Admin',
                'last_name': 'Karams',
                'papel': Papel.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'vendedor',
                'password': 'vendedor123',
                'email': 'vendedor@karams.com.br',
                'first_name': 'Vendedora',
                'last_name': 'Karams',
                'papel': Papel.VENDEDOR,
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        for dados in usuarios:
            password = dados.pop('password')
            username = dados['username']
            user, created = Usuario.objects.get_or_create(
                username=username,
                defaults=dados,
            )
            if created or options['force']:
                user.set_password(password)
                for key, val in dados.items():
                    setattr(user, key, val)
                user.save()
                status = 'criado' if created else 'atualizado'
                self.stdout.write(self.style.SUCCESS(f'Usuário {username} {status}.'))
            else:
                self.stdout.write(f'Usuário {username} já existe (use --force para resetar).')

        MetaMensal.objects.get_or_create(
            vendedor=None,
            mes=hoje.month,
            ano=hoje.year,
            defaults={'meta_contatos': 60, 'meta_vendas': 80000},
        )
        self.stdout.write(self.style.SUCCESS('Metas da equipe configuradas.'))
