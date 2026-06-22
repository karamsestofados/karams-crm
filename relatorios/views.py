from datetime import date as date_cls

from django.http import FileResponse, HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario
from clientes.models import (
    CategoriaCliente,
    ModalidadeCliente,
    OrigemLead,
    Produto,
    RegiaoAtuacao,
    SegmentoCliente,
    StatusFunil,
    TipoCliente,
)
from comissoes.services.produtividade import (
    calcular_realizado,
    conversao_orcamentos,
    taxa_conversao,
)
from relacionamento.services.cockpit import clientes_sem_contato


def _parse_filtros_cliente(request):
    return {
        'categoria': request.GET.get('categoria', 'todos'),
        'tipo_cliente': request.GET.get('tipo_cliente', 'todos'),
        'modalidade_cliente': request.GET.get('modalidade_cliente', 'todos'),
        'segmento': request.GET.get('segmento', 'todos'),
        'origem_lead': request.GET.get('origem_lead', 'todos'),
        'status_funil': request.GET.get('status_funil', 'todos'),
        'regiao_atuacao': request.GET.get('regiao_atuacao', 'todos'),
        'com_pedido_fechado': request.GET.get('com_pedido_fechado', ''),
    }


def _parse_periodo(request):
    hoje = timezone.localdate()
    de = request.GET.get('de', '')
    ate = request.GET.get('ate', '')
    if not de:
        de = hoje.replace(day=1).isoformat()
    if not ate:
        ate = hoje.isoformat()
    try:
        de_date = date_cls.fromisoformat(de)
        ate_date = date_cls.fromisoformat(ate)
    except ValueError:
        de_date = hoje.replace(day=1)
        ate_date = hoje
    return de, ate, de_date, ate_date


def _resolve_alvo(user, vendedor_id):
    if user.is_admin and vendedor_id:
        return Usuario.objects.filter(pk=vendedor_id, papel=Papel.VENDEDOR).first() or user
    if user.is_admin and not vendedor_id:
        return None
    return user


def build_produtividade_context(request):
    user = request.user
    de, ate, de_date, ate_date = _parse_periodo(request)

    vendedor_id = request.GET.get('vendedor', '')
    produto_id = request.GET.get('produto', '')
    regiao = request.GET.get('regiao', '')
    if regiao == 'todos':
        regiao = ''

    filtros_cliente = _parse_filtros_cliente(request)
    alvo = _resolve_alvo(user, vendedor_id)

    realizado = calcular_realizado(
        alvo,
        mes=None,
        ano=None,
        de=de_date,
        ate=ate_date,
        produto_id=produto_id or None,
        regiao=regiao or None,
        filtros_cliente=filtros_cliente,
    )
    conversao = taxa_conversao(
        alvo,
        de=de_date,
        ate=ate_date,
        regiao=regiao or None,
        filtros_cliente=filtros_cliente,
    )
    conversao_orc = conversao_orcamentos(
        alvo,
        de=de_date,
        ate=ate_date,
        produto_id=produto_id or None,
        regiao=regiao or None,
        filtros_cliente=filtros_cliente,
    )

    sem_contato_user = alvo if alvo else user
    clientes_sc = clientes_sem_contato(
        sem_contato_user,
        dias=30,
        limit=100,
        filtros_cliente=filtros_cliente,
    )

    filtros = {
        'de': de,
        'ate': ate,
        'vendedor': vendedor_id,
        'produto': produto_id,
        'regiao': regiao,
        **filtros_cliente,
    }

    context = {
        'filtros': filtros,
        'realizado': realizado,
        'conversao': conversao,
        'conversao_orcamentos': conversao_orc,
        'clientes_sem_contato': clientes_sc,
        'produtos': Produto.objects.ativos().order_by('nome'),
        'regioes': [('todos', 'Todas')] + list(RegiaoAtuacao.choices),
        'categorias': [('todos', 'Todas')] + list(CategoriaCliente.choices),
        'tipos_cliente': [('todos', 'Todos')] + list(TipoCliente.choices),
        'modalidades_cliente': [('todos', 'Todos')] + list(ModalidadeCliente.choices),
        'segmentos': [('todos', 'Todos')] + list(SegmentoCliente.choices),
        'origens_lead': [('todos', 'Todas')] + list(OrigemLead.choices),
        'status_funil_opcoes': [('todos', 'Todos')] + list(StatusFunil.choices),
    }
    if user.is_admin:
        context['vendedores'] = Usuario.objects.filter(
            papel=Papel.VENDEDOR, ativo=True,
        ).order_by('first_name')
    return context


class ProdutividadeExportXlsxView(VendedorRequiredMixin, View):
    def get(self, request):
        context = build_produtividade_context(request)
        from .services.export_produtividade import gerar_xlsx_produtividade

        buffer = gerar_xlsx_produtividade(context)
        filename = f'produtividade_{timezone.localdate().isoformat()}.xlsx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )


class ProdutividadeExportPdfView(VendedorRequiredMixin, View):
    def get(self, request):
        context = build_produtividade_context(request)
        from .services.export_produtividade import gerar_pdf_produtividade

        try:
            buffer = gerar_pdf_produtividade(context)
        except Exception:
            return HttpResponse('Erro ao gerar PDF.', status=500)
        filename = f'produtividade_{timezone.localdate().isoformat()}.pdf'
        return FileResponse(buffer, as_attachment=True, filename=filename, content_type='application/pdf')


class ProdutividadeComercialView(VendedorRequiredMixin, TemplateView):
    template_name = 'relatorios/produtividade.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_produtividade_context(self.request))
        return context
