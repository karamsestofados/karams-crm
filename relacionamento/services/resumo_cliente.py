from django.db.models import Avg, Case, Count, IntegerField, Q, When

from relacionamento.models import (
    AtividadeCliente,
    HumorCliente,
    ProximaAcao,
    Resultado,
    TipoContato,
)

HUMOR_SCORE = {
    HumorCliente.MUITO_RECEPTIVO: 5,
    HumorCliente.RECEPTIVO: 4,
    HumorCliente.NEUTRO: 3,
    HumorCliente.RESISTENTE: 2,
    HumorCliente.INSATISFEITO: 1,
}

HUMOR_LABEL = {v: k.label for k, v in HUMOR_SCORE.items()}


def resumo_comercial_cliente(cliente):
    atividades = AtividadeCliente.objects.ativas().filter(cliente=cliente)
    ultima = atividades.order_by('-data_criacao').first()

    proxima_pendente = (
        atividades
        .filter(concluida=False)
        .exclude(proxima_acao=ProximaAcao.SEM_ACAO)
        .exclude(data_proxima_acao__isnull=True)
        .order_by('data_proxima_acao')
        .first()
    )

    total = atividades.count()
    propostas = atividades.filter(
        Q(tipo_contato=TipoContato.PROPOSTA) | Q(resultado=Resultado.PROPOSTA_ENVIADA)
    ).count()
    negociacoes = atividades.filter(
        Q(tipo_contato=TipoContato.NEGOCIACAO)
        | Q(resultado=Resultado.AGUARDANDO_RETORNO)
    ).count()

    humor_avg = None
    humor_label = '—'
    humores = [
        HUMOR_SCORE[a.humor_cliente]
        for a in atividades.exclude(humor_cliente__isnull=True).exclude(humor_cliente='')
        if a.humor_cliente in HUMOR_SCORE
    ]
    if humores:
        humor_avg = round(sum(humores) / len(humores), 1)
        humor_label = HUMOR_LABEL.get(round(humor_avg), 'Neutro')

    return {
        'ultima_atividade': ultima,
        'proxima_pendente': proxima_pendente,
        'total_interacoes': total,
        'total_propostas': propostas,
        'total_negociacoes': negociacoes,
        'humor_medio': humor_avg,
        'humor_medio_label': humor_label,
    }
