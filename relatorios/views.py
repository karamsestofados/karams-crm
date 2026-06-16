from django.utils import timezone
from django.views.generic import TemplateView

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario
from clientes.models import Produto, RegiaoAtuacao
from comissoes.services.produtividade import calcular_realizado, taxa_conversao
from relacionamento.services.cockpit import clientes_sem_contato


class ProdutividadeComercialView(VendedorRequiredMixin, TemplateView):
    template_name = 'relatorios/produtividade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        user = request.user
        hoje = timezone.localdate()

        de = request.GET.get('de', '')
        ate = request.GET.get('ate', '')
        if not de:
            de = hoje.replace(day=1).isoformat()
        if not ate:
            ate = hoje.isoformat()

        vendedor_id = request.GET.get('vendedor', '')
        produto_id = request.GET.get('produto', '')
        regiao = request.GET.get('regiao', '')
        if regiao == 'todos':
            regiao = ''

        alvo = user
        if user.is_admin and vendedor_id:
            alvo = Usuario.objects.filter(pk=vendedor_id, papel=Papel.VENDEDOR).first() or user
        elif user.is_admin and not vendedor_id:
            alvo = None

        from datetime import date as date_cls
        try:
            de_date = date_cls.fromisoformat(de)
            ate_date = date_cls.fromisoformat(ate)
        except ValueError:
            de_date = hoje.replace(day=1)
            ate_date = hoje

        realizado = calcular_realizado(
            alvo,
            mes=None,
            ano=None,
            de=de_date,
            ate=ate_date,
            produto_id=produto_id or None,
            regiao=regiao or None,
        )
        conversao = taxa_conversao(
            alvo,
            de=de_date,
            ate=ate_date,
            regiao=regiao or None,
        )

        context['filtros'] = {
            'de': de,
            'ate': ate,
            'vendedor': vendedor_id,
            'produto': produto_id,
            'regiao': regiao,
        }
        context['realizado'] = realizado
        context['conversao'] = conversao
        context['clientes_sem_contato'] = clientes_sem_contato(user, dias=30, limit=100)

        if user.is_admin:
            context['vendedores'] = Usuario.objects.filter(
                papel=Papel.VENDEDOR, ativo=True,
            ).order_by('first_name')
        context['produtos'] = Produto.objects.ativos().order_by('nome')
        context['regioes'] = [('todos', 'Todas')] + list(RegiaoAtuacao.choices)

        return context
