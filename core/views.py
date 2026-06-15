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

        clientes = Cliente.objects.para_usuario(user).ativos_no_sistema()
        context['total_clientes'] = clientes.count()
        context['clientes_ativos'] = clientes.filter(categoria='ativo').count()
        context['clientes_adormecidos'] = clientes.filter(categoria='adormecido').count()
        context['clientes_prospeccao'] = clientes.filter(categoria='prospeccao').count()

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
        context['papel'] = user.get_papel_display()
        return context
