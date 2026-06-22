from datetime import date as date_cls

from django.utils import timezone

from powerup.services.conversao import conversao_por_vendedor
from powerup.services.funil import funil_comercial
from powerup.services.gamificacao import conquistas_mes_atual
from powerup.services.motivo_perda import relatorio_motivo_perda
from powerup.services.radar import radar_comercial
from powerup.services.saude_carteira import saude_carteira
from powerup.services.tempo_fechamento import tempo_medio_fechamento


def build_powerup_context(request):
    user = request.user
    hoje = timezone.localdate()
    de = hoje.replace(day=1)
    ate = hoje

    de_param = request.GET.get('de', '')
    ate_param = request.GET.get('ate', '')
    if de_param:
        try:
            de = date_cls.fromisoformat(de_param)
        except ValueError:
            pass
    if ate_param:
        try:
            ate = date_cls.fromisoformat(ate_param)
        except ValueError:
            pass

    return {
        'periodo': {'de': de.isoformat(), 'ate': ate.isoformat()},
        'funil': funil_comercial(user, de, ate),
        'conversao_vendedores': conversao_por_vendedor(de, ate, user),
        'tempo_fechamento': tempo_medio_fechamento(de, ate, user),
        'motivo_perda': relatorio_motivo_perda(user, de, ate),
        'radar': radar_comercial(user),
        'gamificacao': conquistas_mes_atual(),
        'saude': saude_carteira(user),
    }
