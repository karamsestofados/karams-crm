from datetime import timedelta

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente
from relacionamento.models import AtividadeCliente


def _dias_limite():
    return getattr(settings, 'ADORMECIMENTO_DIAS', 30)


def reativar_cliente_apos_interacao(cliente):
    if cliente.categoria == CategoriaCliente.INATIVO:
        return False
    if cliente.categoria == CategoriaCliente.ATIVO:
        return False
    cliente.categoria = CategoriaCliente.ATIVO
    cliente.save(update_fields=['categoria', 'updated_at'])
    return True


def processar_clientes_adormecidos(dias=None):
    dias = dias if dias is not None else _dias_limite()
    limite = timezone.now() - timedelta(days=dias)

    qs = (
        Cliente.objects.filter(categoria=CategoriaCliente.ATIVO)
        .annotate(
            ultima_interacao=Max(
                'atividades__data_criacao',
                filter=Q(atividades__deleted_at__isnull=True),
            ),
        )
        .filter(
            Q(ultima_interacao__lt=limite)
            | Q(ultima_interacao__isnull=True, created_at__lte=limite),
        )
    )
    return qs.update(categoria=CategoriaCliente.ADORMECIDO)


def cliente_sem_contato(cliente, dias=None, hoje=None):
    """Indica se o cliente está há `dias` ou mais sem qualquer interação."""
    dias = dias if dias is not None else _dias_limite()
    hoje = hoje or timezone.localdate()
    limite = timezone.now() - timedelta(days=dias)

    ultima = (
        AtividadeCliente.objects.ativas()
        .filter(cliente=cliente)
        .order_by('-data_criacao')
        .values_list('data_criacao', flat=True)
        .first()
    )
    if ultima:
        return ultima < limite
    created = cliente.created_at
    if not created:
        return False
    return created <= limite
