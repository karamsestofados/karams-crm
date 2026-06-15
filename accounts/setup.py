from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import Papel, Usuario
from comissoes.models import MetaMensal

ADMIN_USERNAME = 'admin'


def _get_admin():
    return Usuario.objects.filter(username=ADMIN_USERNAME, is_active=True).first()


def precisa_configuracao_inicial():
    admin = _get_admin()
    if admin is None:
        return True
    return not admin.has_usable_password()


@transaction.atomic
def definir_senha_admin(*, password):
    if not precisa_configuracao_inicial():
        raise ValueError('A senha do administrador já foi definida.')

    admin = _get_admin()
    if admin is None:
        admin = Usuario(
            username=ADMIN_USERNAME,
            email='admin@karams.com.br',
            first_name='Admin',
            last_name='Karams',
        )

    admin.set_password(password)
    admin.papel = Papel.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.is_active = True
    if not admin.email:
        admin.email = 'admin@karams.com.br'
    admin.save()

    hoje = timezone.localdate()
    MetaMensal.objects.get_or_create(
        vendedor=None,
        mes=hoje.month,
        ano=hoje.year,
        defaults={
            'meta_contatos': settings.METAS_PADRAO_CONTATOS,
            'meta_vendas': settings.METAS_PADRAO_VENDAS,
        },
    )

    return admin


def invalidar_senha_admin():
    """Marca o admin para redefinir senha na próxima visita (após cada deploy)."""
    admin, created = Usuario.objects.get_or_create(
        username=ADMIN_USERNAME,
        defaults={
            'email': 'admin@karams.com.br',
            'first_name': 'Admin',
            'last_name': 'Karams',
            'papel': Papel.ADMIN,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True,
        },
    )
    admin.set_unusable_password()
    admin.papel = Papel.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.is_active = True
    admin.save(update_fields=['password', 'papel', 'is_staff', 'is_superuser', 'is_active'])
    return admin, created
