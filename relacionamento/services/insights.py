from django.urls import reverse
from django.utils import timezone

from relacionamento.services.cockpit import clientes_sem_contato, resumo_dia
from relacionamento.services.rotina_diaria import rotina_diaria_para_usuario


def _insight(prioridade, titulo, descricao, acao_label='', acao_url='', acao_hx_get='', acao_hx_target=''):
    return {
        'prioridade': prioridade,
        'titulo': titulo,
        'descricao': descricao,
        'acao_label': acao_label,
        'acao_url': acao_url,
        'acao_hx_get': acao_hx_get,
        'acao_hx_target': acao_hx_target,
    }


def gerar_insights_cockpit(usuario, limit=6):
    hoje = timezone.localdate()
    rotina = rotina_diaria_para_usuario(usuario)
    resumo = resumo_dia(usuario)
    kpis = resumo['kpis']
    insights = []

    atrasadas = list(rotina['atrasadas'][:3])
    if atrasadas:
        n = rotina['atrasadas'].count()
        titulo = f'{n} follow-up{"s" if n > 1 else ""} atrasado{"s" if n > 1 else ""}'
        nomes = ', '.join(a.cliente.nome for a in atrasadas[:2])
        if n > 2:
            nomes += f' e mais {n - 2}'
        insights.append(_insight(
            'danger',
            titulo,
            f'Priorize contato hoje: {nomes}.',
            acao_label='Ver atrasadas',
            acao_url='#atividade-diaria-content',
        ))

    hoje_list = list(rotina['hoje'][:2])
    if hoje_list:
        for atv in hoje_list:
            hora = atv.hora_proxima_acao.strftime('%H:%M') if atv.hora_proxima_acao else '—'
            insights.append(_insight(
                'warning',
                f'Compromisso hoje — {atv.cliente.nome}',
                f'{atv.get_proxima_acao_display()} às {hora}.',
                acao_label='Registrar resultado',
                acao_hx_get=reverse('atividade:concluir_followup', args=[atv.pk]),
            acao_hx_target='#modal-concluir-container',
            ))

    for item in clientes_sem_contato(usuario, limit=3):
        cliente = item['cliente']
        dias = item['dias_sem_contato']
        insights.append(_insight(
            'danger',
            f'Sem contato — {cliente.nome}',
            f'{dias} dias sem interação. Retome o relacionamento.',
            acao_label='Registrar contato',
            acao_hx_get=reverse('atividade:interacao_nova') + f'?cliente={cliente.pk}',
            acao_hx_target='#modal-interacao-global-container',
        ))

    if kpis.get('negociacoes_abertas', 0) > 0:
        n = kpis['negociacoes_abertas']
        insights.append(_insight(
            'warning',
            f'{n} negociação{"ões" if n > 1 else ""} em aberto',
            'Clientes aguardando retorno ou follow-up pendente.',
            acao_label='Ver relatório',
            acao_url=reverse('relacionamento:relatorio'),
        ))

    proximas = list(rotina['proximas'][:1])
    if proximas and len(insights) < limit:
        atv = proximas[0]
        data_fmt = atv.data_proxima_acao.strftime('%d/%m/%Y') if atv.data_proxima_acao else '—'
        insights.append(_insight(
            'info',
            f'Próximo: {atv.cliente.nome}',
            f'{atv.get_proxima_acao_display()} em {data_fmt}.',
            acao_label='Abrir cliente',
            acao_url=reverse('clientes:lista') + f'?id={atv.cliente.pk}&tab=historico',
        ))

    meta_dia = meta_do_dia(usuario)
    if meta_dia['realizado_contatos'] < meta_dia['meta_contatos'] and len(insights) < limit:
        contatos_hoje = meta_dia['realizado_contatos']
        insights.append(_insight(
            'info',
            'Meta de contatos do dia',
            f'Você registrou {contatos_hoje} contato{"s" if contatos_hoje != 1 else ""} hoje. Meta: {meta_dia["meta_contatos"]}.',
            acao_label='Registrar interação',
            acao_hx_get=reverse('atividade:interacao_nova'),
            acao_hx_target='#modal-interacao-global-container',
        ))

    if not insights and resumo['interacoes_hoje'] == 0:
        insights.append(_insight(
            'info',
            'Comece o dia',
            'Nenhuma interação registrada hoje. Registre o primeiro contato.',
            acao_label='Registrar interação',
            acao_hx_get=reverse('atividade:interacao_nova'),
            acao_hx_target='#modal-interacao-global-container',
        ))

    return insights[:limit]
