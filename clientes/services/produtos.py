from django.core.exceptions import ValidationError

from clientes.models import Cliente, ClienteProduto, Produto, TipoProduto


def produtos_disponiveis_para(cliente):
    """Produtos ativos que podem ser vinculados ao cliente."""
    ja_vinculados = cliente.vinculos_produto.values_list('produto_id', flat=True)
    return Produto.objects.ativos().exclude(pk__in=ja_vinculados).order_by('nome')


def obter_alerta_vinculo(produto, cliente_destino):
    """Retorna alerta ao vincular produto EXCLUSIVO/UNICO já ligado a outro(s) cliente(s)."""
    if produto.tipo_produto == TipoProduto.PADRAO:
        return None

    outros = list(
        ClienteProduto.objects.filter(produto=produto)
        .exclude(cliente=cliente_destino)
        .select_related('cliente')
        .order_by('cliente__nome')
    )
    if not outros:
        return None

    clientes = [v.cliente.nome for v in outros]
    bloquear = produto.tipo_produto == TipoProduto.UNICO
    nivel = 'alto' if bloquear else 'medio'

    return {
        'tipo': produto.tipo_produto,
        'tipo_label': produto.get_tipo_produto_display(),
        'produto_nome': produto.nome,
        'nivel': nivel,
        'clientes': clientes,
        'bloquear': bloquear,
    }


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
