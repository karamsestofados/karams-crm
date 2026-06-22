from django.utils import timezone

from accounts.models import Papel, Usuario
from comissoes.models import ConquistaVendedor, TipoConquista


def conquistas_mes_atual(mes=None, ano=None):
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year

    vendedores = Usuario.objects.filter(papel=Papel.VENDEDOR, ativo=True).order_by('first_name')
    blocos = []

    for v in vendedores:
        conquistas = ConquistaVendedor.objects.filter(
            usuario=v,
            mes=mes,
            ano=ano,
        ).order_by('-data_conquista')
        if not conquistas.exists():
            conquistas = ConquistaVendedor.objects.filter(
                usuario=v,
                mes__isnull=True,
                ano__isnull=True,
            ).order_by('-data_conquista')[:3]
        if conquistas.exists():
            blocos.append({
                'vendedor': v,
                'nome': v.get_full_name() or v.username,
                'conquistas': list(conquistas),
            })

    destaques = []
    for tipo, emoji, titulo in (
        (TipoConquista.STREAK_META_7, '🔥', 'dias seguidos cumprindo meta'),
        (TipoConquista.REI_WHATSAPP, '🥇', 'Rei do WhatsApp'),
        (TipoConquista.MESTRE_FOLLOWUP, '🥇', 'Mestre do Follow-up'),
    ):
        c = ConquistaVendedor.objects.filter(tipo=tipo, mes=mes, ano=ano).select_related('usuario').first()
        if c:
            destaques.append({
                'emoji': emoji,
                'titulo': titulo,
                'vendedor': c.usuario.get_full_name() or c.usuario.username,
                'descricao': c.get_tipo_display(),
            })

    return {'blocos': blocos, 'destaques': destaques}
