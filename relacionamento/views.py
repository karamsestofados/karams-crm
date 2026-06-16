from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario
from clientes.models import Cliente, Produto
from clientes.views import get_cliente_or_403

from .constants import TIMELINE_FILTROS
from .forms import AtividadeClienteForm, ConcluirFollowupForm, InteracaoGlobalForm
from .models import AtividadeCliente, TipoContato
from .services.atividades import concluir_followup, registrar_interacao
from .services.cockpit import contexto_cockpit_completo
from .services.external_calendar.dispatcher import resolve_calendar_url
from .services.relatorio import filtrar_atividades, indicadores_por_tipo, ranking_vendedores
from .services.resumo_cliente import resumo_comercial_cliente


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _cockpit_context(request, dia_selecionado=None):
    hoje = timezone.localdate()
    ano = _parse_int(request.GET.get('ano'), hoje.year)
    mes = _parse_int(request.GET.get('mes'), hoje.month)

    if dia_selecionado is None:
        dia_str = request.GET.get('dia')
        if dia_str:
            try:
                parts = dia_str.split('-')
                dia_selecionado = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except (ValueError, IndexError):
                dia_selecionado = hoje
        else:
            dia_selecionado = hoje

    return contexto_cockpit_completo(
        request.user,
        ano=ano,
        mes=mes,
        dia_selecionado=dia_selecionado,
    )


def _render_cockpit_main(request, calendar_url=None):
    context = _cockpit_context(request)
    if calendar_url:
        context['google_calendar_url'] = calendar_url
    return render(request, 'relacionamento/partials/cockpit_main.html', context)


def _interacao_success_message(calendar_url=None):
    if calendar_url:
        return 'Interação registrada com sucesso. Use o botão abaixo para salvar no Google Agenda.'
    return 'Interação registrada com sucesso.'


def _concluir_success_message(calendar_url=None):
    if calendar_url:
        return 'Resultado registrado. Use o botão abaixo para salvar no Google Agenda.'
    return 'Resultado registrado e nova atividade gerada.'


def _finalize_interacao_response(request, calendar_url, render_response, redirect_url):
    if request.headers.get('HX-Request'):
        return render_response
    if calendar_url:
        request.session['pending_calendar_url'] = calendar_url
    return redirect(redirect_url)


class AtividadeDiariaView(VendedorRequiredMixin, TemplateView):
    template_name = 'relacionamento/atividade_diaria.html'

    def get(self, request, *args, **kwargs):
        if request.headers.get('HX-Request'):
            return _render_cockpit_main(request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_cockpit_context(self.request))
        context['tipos_contato'] = TipoContato
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
                    hora_proxima_acao=form.cleaned_data.get('hora_proxima_acao'),
                    valor_venda=form.cleaned_data.get('valor_venda'),
                )
                calendar_url = resolve_calendar_url(
                    atividade.cliente, request.user, form.cleaned_data,
                )
                messages.success(request, _concluir_success_message(calendar_url))
                return _finalize_interacao_response(
                    request,
                    calendar_url,
                    _render_cockpit_main(request, calendar_url),
                    'atividade:atividade_diaria',
                )
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

        return redirect('atividade:atividade_diaria')


class InteracaoGlobalCreateView(VendedorRequiredMixin, View):
    def get(self, request):
        tipo = request.GET.get('tipo', TipoContato.OUTRO)
        cliente_id = request.GET.get('cliente')
        cliente = None
        if cliente_id:
            cliente = get_cliente_or_403(request.user, cliente_id)

        form = InteracaoGlobalForm(
            user=request.user,
            cliente=cliente,
            initial={'tipo_contato': tipo},
        )
        return render(request, 'relacionamento/partials/modal_interacao_global.html', {
            'form': form,
            'tipo_preset': tipo,
        })

    def post(self, request):
        form = InteracaoGlobalForm(request.POST, user=request.user)
        if form.is_valid():
            cliente = form.cleaned_data['cliente']
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
                    hora_proxima_acao=form.cleaned_data.get('hora_proxima_acao'),
                    valor_venda=form.cleaned_data.get('valor_venda'),
                )
                calendar_url = resolve_calendar_url(cliente, request.user, form.cleaned_data)
                messages.success(request, _interacao_success_message(calendar_url))
                return _finalize_interacao_response(
                    request,
                    calendar_url,
                    _render_cockpit_main(request, calendar_url),
                    'atividade:atividade_diaria',
                )
            except ValidationError as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
                if request.headers.get('HX-Request'):
                    return render(request, 'relacionamento/partials/modal_interacao_global.html', {
                        'form': form,
                    }, status=422)
        else:
            if request.headers.get('HX-Request'):
                return render(request, 'relacionamento/partials/modal_interacao_global.html', {
                    'form': form,
                }, status=422)

        return redirect('atividade:atividade_diaria')


class CalendarioDiaPartialView(VendedorRequiredMixin, View):
    def get(self, request, data_str):
        try:
            parts = data_str.split('-')
            dia = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return redirect('atividade:atividade_diaria')

        from .services.cockpit import eventos_do_dia

        return render(request, 'relacionamento/partials/cockpit_calendario_dia.html', {
            'dia_selecionado': dia,
            'eventos_dia': eventos_do_dia(request.user, dia),
        })


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
        cliente = get_cliente_or_403(request.user, pk)
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
                    hora_proxima_acao=form.cleaned_data.get('hora_proxima_acao'),
                    valor_venda=form.cleaned_data.get('valor_venda'),
                )
                calendar_url = resolve_calendar_url(cliente, request.user, form.cleaned_data)
                messages.success(request, _interacao_success_message(calendar_url))
                redirect_url = reverse('clientes:lista') + f'?id={pk}&tab=historico'
                if request.headers.get('HX-Request'):
                    ctx = _cliente_tab_context(cliente)
                    ctx['google_calendar_url'] = calendar_url
                    return render(
                        request,
                        'relacionamento/partials/relacionamento_tab.html',
                        ctx,
                    )
                if calendar_url:
                    request.session['pending_calendar_url'] = calendar_url
                return redirect(redirect_url)
            except ValidationError as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
                if request.headers.get('HX-Request'):
                    return render(
                        request,
                        'relacionamento/partials/relacionamento_tab.html',
                        _cliente_tab_context(cliente, form),
                    )
        else:
            if request.headers.get('HX-Request'):
                return render(
                    request,
                    'relacionamento/partials/relacionamento_tab.html',
                    _cliente_tab_context(cliente, form),
                )

        url = reverse('clientes:lista') + f'?id={pk}&tab=historico'
        return redirect(url)


def _cliente_tab_context(cliente, form=None, tipo_filtro=''):
    qs = AtividadeCliente.objects.ativas().filter(cliente=cliente).select_related('usuario', 'produto_relacionado')
    if tipo_filtro:
        qs = qs.filter(tipo_contato=tipo_filtro)
    return {
        'cliente_selecionado': cliente,
        'atividades': qs.order_by('-data_criacao')[:50],
        'resumo_comercial': resumo_comercial_cliente(cliente),
        'atividade_form': form or AtividadeClienteForm(cliente=cliente),
        'tipo_filtro': tipo_filtro,
        'timeline_filtros': TIMELINE_FILTROS,
    }


class ClienteTimelinePartialView(VendedorRequiredMixin, View):
    def get(self, request, pk):
        cliente = get_cliente_or_403(request.user, pk)
        tipo_filtro = request.GET.get('tipo', '')
        return render(request, 'relacionamento/partials/relacionamento_tab.html', _cliente_tab_context(cliente, tipo_filtro=tipo_filtro))
