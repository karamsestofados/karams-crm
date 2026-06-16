from django.utils import timezone

from relacionamento.models import AtividadeCliente


def rotina_diaria_para_usuario(usuario):
    qs = (
        AtividadeCliente.objects
        .pendentes_para_usuario(usuario)
        .select_related('cliente', 'cliente__vendedor', 'produto_relacionado', 'usuario')
        .order_by('data_proxima_acao', 'hora_proxima_acao', 'cliente__nome')
    )
    hoje = timezone.localdate()
    return {
        'hoje': qs.filter(data_proxima_acao=hoje),
        'atrasadas': qs.filter(data_proxima_acao__lt=hoje),
        'proximas': qs.filter(data_proxima_acao__gt=hoje),
    }
