from datetime import timedelta

from django.utils import timezone

from clientes.models import CategoriaCliente, Cliente, StatusFunil
from relacionamento.models import AtividadeCliente, HumorCliente, Resultado
from relacionamento.services.cockpit import clientes_sem_contato


def _clientes_orcamento_sem_retorno(usuario, dias=7):
    hoje = timezone.localdate()
    limite = hoje - timedelta(days=dias)
    qs = Cliente.objects.para_usuario(usuario).ativos().filter(
        status_funil__in=(
            StatusFunil.PROPOSTA_ENVIADA,
            StatusFunil.AGUARDANDO_RETORNO,
        ),
    )
    resultado = []
    for cliente in qs:
        ultima = (
            AtividadeCliente.objects.ativas()
            .filter(cliente=cliente)
            .order_by('-data_criacao')
            .first()
        )
        if not ultima:
            continue
        if ultima.data_criacao.date() <= limite:
            resultado.append(cliente)
    return resultado


def _clientes_aguardando_fotos(usuario):
    qs = Cliente.objects.para_usuario(usuario).ativos()
    resultado = []
    for cliente in qs:
        ultima = (
            AtividadeCliente.objects.ativas()
            .filter(cliente=cliente)
            .order_by('-data_criacao')
            .first()
        )
        if not ultima:
            continue
        texto = f'{(ultima.resumo or "")} {(ultima.assunto or "")}'.lower()
        if 'foto' in texto or ultima.resultado == Resultado.AGUARDANDO_RETORNO:
            resultado.append(cliente)
    return resultado[:50]


def _clientes_proximos_fechar(usuario):
    hoje = timezone.localdate()
    limite = hoje - timedelta(days=7)
    qs = Cliente.objects.para_usuario(usuario).ativos().filter(
        status_funil=StatusFunil.NEGOCIACAO,
    )
    resultado = []
    for cliente in qs:
        ultima = (
            AtividadeCliente.objects.ativas()
            .filter(cliente=cliente, data_criacao__date__gte=limite)
            .order_by('-data_criacao')
            .first()
        )
        if ultima and ultima.humor_cliente in (
            HumorCliente.MUITO_RECEPTIVO,
            HumorCliente.RECEPTIVO,
            None,
        ):
            resultado.append(cliente)
    return resultado


def radar_comercial(usuario):
    orc_sem_retorno = _clientes_orcamento_sem_retorno(usuario)
    aguardando_fotos = _clientes_aguardando_fotos(usuario)
    sem_contato = clientes_sem_contato(usuario, dias=20, limit=100)
    proximos = _clientes_proximos_fechar(usuario)

    return [
        {
            'nivel': 'danger',
            'icone': '🔴',
            'titulo': f'{len(orc_sem_retorno)} clientes com orçamento sem retorno',
            'clientes': orc_sem_retorno[:8],
        },
        {
            'nivel': 'warning',
            'icone': '🟠',
            'titulo': f'{len(aguardando_fotos)} clientes aguardando fotos',
            'clientes': aguardando_fotos[:8],
        },
        {
            'nivel': 'caution',
            'icone': '🟡',
            'titulo': f'{len(sem_contato)} clientes sem contato há 20 dias',
            'clientes': [item['cliente'] for item in sem_contato[:8]],
        },
        {
            'nivel': 'success',
            'icone': '🟢',
            'titulo': f'{len(proximos)} clientes próximos de fechar',
            'clientes': proximos[:8],
        },
    ]
