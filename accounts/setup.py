from django.db import transaction
from django.utils import timezone

from accounts.models import Papel, Usuario
from comissoes.models import MetaMensal


def precisa_configuracao_inicial():
    return not Usuario.objects.filter(is_superuser=True, is_active=True).exists()


@transaction.atomic
def criar_admin_inicial(*, username, password, email, first_name, last_name, meta_contatos, meta_vendas):
    if not precisa_configuracao_inicial():
        raise ValueError('A configuração inicial já foi concluída.')

    admin = Usuario.objects.create_user(
        username=username,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        papel=Papel.ADMIN,
        is_staff=True,
        is_superuser=True,
    )

    hoje = timezone.localdate()
    MetaMensal.objects.get_or_create(
        vendedor=None,
        mes=hoje.month,
        ano=hoje.year,
        defaults={
            'meta_contatos': meta_contatos,
            'meta_vendas': meta_vendas,
        },
    )

    return admin
