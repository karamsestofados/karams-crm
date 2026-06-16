from django.core.exceptions import ValidationError

from clientes.models import Cliente, ClienteProduto, Produto, TipoProduto


def produtos_disponiveis_para(cliente):
    """Produtos ativos que podem ser vinculados ao cliente."""
    ja_vinculados = cliente.vinculos_produto.values_list('produto_id', flat=True)
    qs = Produto.objects.ativos().exclude(pk__in=ja_vinculados)

    unicos_ocupados = ClienteProduto.objects.filter(
        produto__tipo_produto=TipoProduto.UNICO,
    ).exclude(cliente=cliente).values_list('produto_id', flat=True)

    return qs.exclude(pk__in=unicos_ocupados).order_by('nome')


def vincular_produto(cliente, produto, observacoes=''):
    if not produto.ativo:
        raise ValidationError('Este produto está inativo e não pode ser vinculado.')

    if cliente.vinculos_produto.filter(produto=produto).exists():
        raise ValidationError(f'"{produto.nome}" já está vinculado a este cliente.')

    if produto.tipo_produto == TipoProduto.UNICO:
        existing = ClienteProduto.objects.filter(produto=produto).select_related('cliente').first()
        if existing:
            raise ValidationError(
                f'Produto único "{produto.nome}" já pertence a "{existing.cliente.nome}". '
                'Não é possível vincular a outro cliente.'
            )

    vinculo = ClienteProduto(
        cliente=cliente,
        produto=produto,
        observacoes=observacoes,
    )
    vinculo.save()
    return vinculo


def desvincular_produto(vinculo):
    vinculo.delete()
