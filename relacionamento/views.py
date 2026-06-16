from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import TemplateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario
from clientes.models import Cliente, Produto
from clientes.views import get_cliente_or_404

from .forms import AtividadeClienteForm, ConcluirFollowupForm
from .models import AtividadeCliente, TipoContato
from .services.atividades import concluir_followup, registrar_interacao
from .services.relatorio import filtrar_atividades, indicadores_por_tipo, ranking_vendedores
from .services.resumo_cliente import resumo_comercial_cliente
from .services.rotina_diaria import rotina_diaria_para_usuario


class AtividadeDiariaView(VendedorRequiredMixin, TemplateView):
    template_name = 'relacionamento/atividade_diaria.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rotina = rotina_diaria_para_usuario(self.request.user)
        context.update(rotina)
        context['total_hoje'] = rotina['hoje'].count()
        context['total_atrasadas'] = rotina['atrasadas'].count()
        context['total_proximas'] = rotina['proximas'].count()
        return context


class ConcluirFollowupView(VendedorRequiredMixin, View):
    def get(self, request, pk):
        atividade = get_object_or_404(
            AtividadeCliente.objects.pendentes_para_usuario(request.user).select_related('cliente'),
            pk=pk,
        )
        form = ConcluirFollowupForm(initial={'tipo_contato': atividade.tipo_contato})
        return render(request, 'relacionamento/partials/modal_concluir.html', {
            'atividade': atividade,
            'form': form,
        })

    def post(self, request, pk):
        atividade = get_object_or_404(
            AtividadeCliente.objects.pendentes_para_usuario(request.user).select_related('cliente'),
            pk=pk,
        )
        form = ConcluirFollowupForm(request.POST)
        if form.is_valid():
            try:
                concluir_followup(
                    atividade,
                    request.user,
                    resumo=form.cleaned_data['resumo'],
                    tipo_contato=form.cleaned_data['tipo_contato'],
                    resultado=form.cleaned_data['resultado'],
                    proxima_acao=form.cleaned_data['proxima_acao'],
                    data_proxima_acao=form.cleaned_data.get('data_proxima_acao'),
                )
                messages.success(request, 'Atividade concluída e nova interação registrada.')
            except ValidationError as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
                if request.headers.get('HX-Request'):
                    return render(request, 'relacionamento/partials/modal_concluir.html', {
                        'atividade': atividade,
                        'form': form,
                    }, status=422)
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'relacionamento/partials/modal_concluir.html', {
                    'atividade': atividade,
                    'form': form,
                }, status=422)

        if request.headers.get('HX-Request'):
            rotina = rotina_diaria_para_usuario(request.user)
            return render(request, 'relacionamento/partials/atividade_diaria_listas.html', rotina)
        return redirect('atividade:atividade_diaria')


class RelatorioRelacionamentoView(VendedorRequiredMixin, TemplateView):
    template_name = 'relacionamento/relatorio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        qs = filtrar_atividades(request)
        context['indicadores'] = indicadores_por_tipo(qs)
        context['ranking'] = ranking_vendedores(qs)
        context['total_interacoes'] = qs.count()
        context['filtros'] = {
            'de': request.GET.get('de', ''),
            'ate': request.GET.get('ate', ''),
            'vendedor': request.GET.get('vendedor', ''),
            'cliente': request.GET.get('cliente', ''),
            'produto': request.GET.get('produto', ''),
            'tipo_contato': request.GET.get('tipo_contato', 'todos'),
        }
        context['tipos_contato'] = [('todos', 'Todos'), *TipoContato.choices]
        if request.user.is_admin:
            context['vendedores'] = Usuario.objects.filter(
                papel=Papel.VENDEDOR, ativo=True,
            ).order_by('first_name')
        context['clientes'] = Cliente.objects.para_usuario(request.user).ativos().order_by('nome')[:200]
        context['produtos'] = Produto.objects.ativos().order_by('nome')
        return context


class ClienteAtividadeCreateView(VendedorRequiredMixin, View):
    def post(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        form = AtividadeClienteForm(request.POST, cliente=cliente)
        if form.is_valid():
            try:
                registrar_interacao(
                    cliente=cliente,
                    usuario=request.user,
                    tipo_contato=form.cleaned_data['tipo_contato'],
                    resumo=form.cleaned_data['resumo'],
                    assunto=form.cleaned_data.get('assunto', ''),
                    resultado=form.cleaned_data['resultado'],
                    humor_cliente=form.cleaned_data.get('humor_cliente'),
                    produto_relacionado=form.cleaned_data.get('produto_relacionado'),
                    proxima_acao=form.cleaned_data['proxima_acao'],
                    data_proxima_acao=form.cleaned_data.get('data_proxima_acao'),
                )
                messages.success(request, 'Interação registrada com sucesso.')
            except ValidationError as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
                if request.headers.get('HX-Request'):
                    return render(request, 'relacionamento/partials/relacionamento_tab.html', {
                        'cliente_selecionado': cliente,
                        'atividades': AtividadeCliente.objects.ativas().filter(cliente=cliente).select_related('usuario', 'produto_relacionado').order_by('-data_criacao')[:50],
                        'resumo_comercial': resumo_comercial_cliente(cliente),
                        'atividade_form': form,
                    }, status=422)
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'relacionamento/partials/relacionamento_tab.html', {
                    'cliente_selecionado': cliente,
                    'atividades': AtividadeCliente.objects.ativas().filter(cliente=cliente).select_related('usuario', 'produto_relacionado').order_by('-data_criacao')[:50],
                    'resumo_comercial': resumo_comercial_cliente(cliente),
                    'atividade_form': form,
                }, status=422)

        if request.headers.get('HX-Request'):
            atividades = (
                AtividadeCliente.objects.ativas()
                .filter(cliente=cliente)
                .select_related('usuario', 'produto_relacionado')
                .order_by('-data_criacao')[:50]
            )
            return render(request, 'relacionamento/partials/relacionamento_tab.html', {
                'cliente_selecionado': cliente,
                'atividades': atividades,
                'resumo_comercial': resumo_comercial_cliente(cliente),
                'atividade_form': AtividadeClienteForm(cliente=cliente),
            })

        url = reverse('clientes:lista') + f'?id={pk}&tab=relacionamento'
        return redirect(url)


class ClienteTimelinePartialView(VendedorRequiredMixin, View):
    def get(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        atividades = (
            AtividadeCliente.objects.ativas()
            .filter(cliente=cliente)
            .select_related('usuario', 'produto_relacionado')
            .order_by('-data_criacao')[:50]
        )
        return render(request, 'relacionamento/partials/relacionamento_tab.html', {
            'cliente_selecionado': cliente,
            'atividades': atividades,
            'resumo_comercial': resumo_comercial_cliente(cliente),
            'atividade_form': AtividadeClienteForm(cliente=cliente),
        })
