import json
from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario
from clientes.models import Cliente, Produto
from clientes.views import get_cliente_or_403

from .constants import TIMELINE_FILTROS
from .forms import AtividadeClienteEditForm, AtividadeClienteForm, ConcluirFollowupForm, InteracaoGlobalForm
from .models import AtividadeCliente, TipoContato
from .services.atividades import concluir_followup, registrar_interacao
from .services.editar_atividade import editar_atividade, pode_editar_atividade
from .services.timeline import montar_timeline_cliente
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
        return 'Interação registrada com sucesso. Abrindo Google Agenda em nova guia.'
    return 'Interação registrada com sucesso.'


def _concluir_success_message(calendar_url=None):
    if calendar_url:
        return 'Resultado registrado. Abrindo Google Agenda em nova guia.'
    return 'Resultado registrado e nova atividade gerada.'


def _attach_calendar_trigger(response, calendar_url):
    if calendar_url:
        response['HX-Trigger'] = json.dumps({'openGoogleCalendar': calendar_url})
    return response


def _modal_error_response(response, retarget_selector):
    response['HX-Retarget'] = retarget_selector
    response['HX-Reswap'] = 'innerHTML'
    return response


def _finalize_interacao_response(request, calendar_url, render_response, redirect_url):
    if request.headers.get('HX-Request'):
        return _attach_calendar_trigger(render_response, calendar_url)
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
                    motivo_perda=form.cleaned_data.get('motivo_perda') or None,
                    motivo_perda_detalhe=form.cleaned_data.get('motivo_perda_detalhe', ''),
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
                    return _modal_error_response(render(request, 'relacionamento/partials/modal_concluir.html', {
                        'atividade': atividade,
                        'form': form,
                    }, status=422), '#modal-concluir-container')
        else:
            if request.headers.get('HX-Request'):
                return _modal_error_response(render(request, 'relacionamento/partials/modal_concluir.html', {
                    'atividade': atividade,
                    'form': form,
                }, status=422), '#modal-concluir-container')

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
                    produtos_relacionados=form.cleaned_data.get('produtos_relacionados'),
                    proxima_acao=form.cleaned_data['proxima_acao'],
                    data_proxima_acao=form.cleaned_data.get('data_proxima_acao'),
                    hora_proxima_acao=form.cleaned_data.get('hora_proxima_acao'),
                    valor_venda=form.cleaned_data.get('valor_venda'),
                    motivo_perda=form.cleaned_data.get('motivo_perda') or None,
                    motivo_perda_detalhe=form.cleaned_data.get('motivo_perda_detalhe', ''),
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
                    return _modal_error_response(render(request, 'relacionamento/partials/modal_interacao_global.html', {
                        'form': form,
                    }, status=422), '#modal-interacao-global-container')
        else:
            if request.headers.get('HX-Request'):
                return _modal_error_response(render(request, 'relacionamento/partials/modal_interacao_global.html', {
                    'form': form,
                }, status=422), '#modal-interacao-global-container')

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
                    produtos_relacionados=form.cleaned_data.get('produtos_relacionados'),
                    proxima_acao=form.cleaned_data['proxima_acao'],
                    data_proxima_acao=form.cleaned_data.get('data_proxima_acao'),
                    hora_proxima_acao=form.cleaned_data.get('hora_proxima_acao'),
                    valor_venda=form.cleaned_data.get('valor_venda'),
                    motivo_perda=form.cleaned_data.get('motivo_perda') or None,
                    motivo_perda_detalhe=form.cleaned_data.get('motivo_perda_detalhe', ''),
                )
                calendar_url = resolve_calendar_url(cliente, request.user, form.cleaned_data)
                messages.success(request, _interacao_success_message(calendar_url))
                redirect_url = reverse('clientes:lista') + f'?id={pk}&tab=historico'
                if request.headers.get('HX-Request'):
                    ctx = _cliente_tab_context(cliente, user=request.user)
                    ctx['google_calendar_url'] = calendar_url
                    return _attach_calendar_trigger(
                        render(
                            request,
                            'relacionamento/partials/relacionamento_tab.html',
                            ctx,
                        ),
                        calendar_url,
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
                        _cliente_tab_context(cliente, form, user=request.user),
                    )
        else:
            if request.headers.get('HX-Request'):
                return render(
                    request,
                    'relacionamento/partials/relacionamento_tab.html',
                    _cliente_tab_context(cliente, form, user=request.user),
                )

        url = reverse('clientes:lista') + f'?id={pk}&tab=historico'
        return redirect(url)


def _cliente_tab_context(
    cliente,
    form=None,
    tipo_filtro='',
    limit=50,
    user=None,
    edit_form=None,
    edit_atividade=None,
    modal_editar_aberto=False,
):
    qs = AtividadeCliente.objects.ativas().filter(cliente=cliente).select_related('usuario').prefetch_related('produtos_relacionados')
    if tipo_filtro:
        qs = qs.filter(tipo_contato=tipo_filtro)
    qs = qs.order_by('-data_criacao')
    if limit:
        atividades_list = list(qs[:limit])
    else:
        atividades_list = list(qs)
    ctx = {
        'cliente_selecionado': cliente,
        'atividades': atividades_list,
        'timeline_eventos': montar_timeline_cliente(cliente, tipo_filtro, limit),
        'resumo_comercial': resumo_comercial_cliente(cliente),
        'atividade_form': form or AtividadeClienteForm(cliente=cliente),
        'tipo_filtro': tipo_filtro,
        'timeline_filtros': TIMELINE_FILTROS,
        'edit_form': edit_form,
        'edit_atividade': edit_atividade,
        'modal_editar_aberto': modal_editar_aberto,
    }
    if user is not None:
        ctx['request_user'] = user
    return ctx


class ClienteAtividadeUpdateView(VendedorRequiredMixin, View):
    def get(self, request, pk, atividade_pk):
        cliente = get_cliente_or_403(request.user, pk)
        atividade = get_object_or_404(AtividadeCliente, pk=atividade_pk, cliente=cliente, deleted_at__isnull=True)
        if not pode_editar_atividade(atividade, request.user):
            raise PermissionDenied('Você não pode editar este registro.')
        form = AtividadeClienteEditForm(instance=atividade, cliente=cliente)
        return render(request, 'relacionamento/partials/modal_editar_atividade.html', {
            'cliente_selecionado': cliente,
            'atividade': atividade,
            'edit_form': form,
        })

    def post(self, request, pk, atividade_pk):
        cliente = get_cliente_or_403(request.user, pk)
        atividade = get_object_or_404(AtividadeCliente, pk=atividade_pk, cliente=cliente, deleted_at__isnull=True)
        if not pode_editar_atividade(atividade, request.user):
            raise PermissionDenied('Você não pode editar este registro.')
        form = AtividadeClienteEditForm(request.POST, instance=atividade, cliente=cliente)
        modal_erro = False
        if form.is_valid():
            try:
                edicao = editar_atividade(atividade, request.user, form.cleaned_data)
                if edicao is None:
                    messages.info(request, 'Nenhuma alteração foi detectada.')
                else:
                    messages.success(request, 'Registro atualizado.')
                if request.headers.get('HX-Request'):
                    return render(
                        request,
                        'relacionamento/partials/relacionamento_tab.html',
                        _cliente_tab_context(cliente, user=request.user),
                    )
            except ValidationError as exc:
                msg = exc.messages[0] if exc.messages else str(exc)
                messages.error(request, msg)
                form.add_error(None, msg)
                modal_erro = True
            except PermissionDenied as exc:
                messages.error(request, str(exc))
                form.add_error(None, str(exc))
                modal_erro = True
        else:
            modal_erro = True
        if request.headers.get('HX-Request'):
            return render(
                request,
                'relacionamento/partials/relacionamento_tab.html',
                _cliente_tab_context(
                    cliente,
                    user=request.user,
                    edit_form=form,
                    edit_atividade=atividade,
                    modal_editar_aberto=modal_erro,
                ),
            )
        return redirect(reverse('clientes:lista') + f'?id={pk}&tab=historico')


class ClienteTimelinePartialView(VendedorRequiredMixin, View):
    def get(self, request, pk):
        cliente = get_cliente_or_403(request.user, pk)
        tipo_filtro = request.GET.get('tipo', '')
        return render(request, 'relacionamento/partials/relacionamento_tab.html', _cliente_tab_context(cliente, tipo_filtro=tipo_filtro, user=request.user))


class ClienteHistoricoPdfView(VendedorRequiredMixin, View):
    def get(self, request, pk):
        cliente = get_cliente_or_403(request.user, pk)
        tipo_filtro = request.GET.get('tipo', '')
        ctx = _cliente_tab_context(cliente, tipo_filtro=tipo_filtro, limit=None)
        ctx['exportado_em'] = timezone.now()
        from .services.export_historico import gerar_pdf_historico_cliente

        try:
            buffer = gerar_pdf_historico_cliente(ctx)
        except Exception:
            return HttpResponse('Erro ao gerar PDF.', status=500)
        safe_name = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in cliente.nome)[:40]
        filename = f'historico_{safe_name}.pdf'
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')
