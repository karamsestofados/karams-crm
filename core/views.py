from django.db.models import Count
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.mixins import VendedorRequiredMixin
from clientes.models import Cliente
from comissoes.models import MetaMensal


class DashboardView(VendedorRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        hoje = timezone.localdate()

        clientes = Cliente.objects.para_usuario(user).ativos()
        ativos = clientes.filter(categoria='ativo').count()
        adormecidos = clientes.filter(categoria='adormecido').count()
        prospeccao = clientes.filter(categoria='prospeccao').count()
        total = clientes.count()

        context['total_clientes'] = total
        context['clientes_ativos'] = ativos
        context['clientes_adormecidos'] = adormecidos
        context['clientes_prospeccao'] = prospeccao
        context['papel'] = user.get_papel_display()
        context['mes_label'] = f'{hoje.month:02d}/{hoje.year}'

        meta = MetaMensal.objects.filter(
            vendedor=user if not user.is_admin else None,
            mes=hoje.month,
            ano=hoje.year,
        ).first()
        if not meta and user.is_admin:
            meta = MetaMensal.objects.filter(
                vendedor__isnull=True,
                mes=hoje.month,
                ano=hoje.year,
            ).first()
        context['meta_mensal'] = meta

        estados_qs = (
            clientes.exclude(estado='')
            .values('estado')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        context['chart_categorias'] = {
            'labels': ['Ativos', 'Adormecidos', 'Prospecção'],
            'values': [ativos, adormecidos, prospeccao],
        }
        context['chart_estados'] = {
            'labels': [e['estado'] for e in estados_qs],
            'values': [e['total'] for e in estados_qs],
        }
        context['sparkline_clientes'] = [prospeccao, adormecidos, ativos, total]
        context['sparkline_contatos'] = [
            0,
            meta.meta_contatos // 4 if meta else 15,
            meta.meta_contatos // 2 if meta else 30,
            meta.meta_contatos if meta else 60,
        ]
        meta_vendas = float(meta.meta_vendas) if meta else 80000
        context['sparkline_vendas'] = [
            0,
            int(meta_vendas * 0.25) if meta else 20000,
            int(meta_vendas * 0.5) if meta else 40000,
            int(meta_vendas) if meta else 80000,
        ]
        context['top_clientes'] = clientes.filter(categoria='ativo').order_by('nome')[:8]

        pct_ativos = round(ativos / total * 100) if total else 0
        context['pct_ativos'] = pct_ativos

        return context
