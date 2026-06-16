from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario

from .forms import CATEGORIAS_REATIVACAO, ClienteForm, ClienteReativarForm, ProdutoForm, VinculoProdutoForm
from .models import (
    CategoriaCliente,
    Cliente,
    ClienteProduto,
    ModalidadeCliente,
    OrigemLead,
    Produto,
    RegiaoAtuacao,
    SegmentoCliente,
    StatusFunil,
    TipoCliente,
)
from .services.produtos import desvincular_produto, produtos_disponiveis_para, vincular_produto

FILTRO_PARAMS = (
    'q', 'categoria', 'vendedor',
    'tipo_cliente', 'modalidade_cliente', 'segmento', 'origem_lead', 'status_funil', 'regiao_atuacao',
)


def build_filtros_query(request, exclude=()):
    parts = []
    for key in FILTRO_PARAMS:
        if key in exclude:
            continue
        val = request.GET.get(key, '')
        if val and val != 'todos':
            parts.append(f'{key}={val}')
    return '&'.join(parts)


def get_cliente_queryset(user):
    return Cliente.objects.para_usuario(user).select_related('vendedor').prefetch_related(
        'vinculos_produto__produto',
    )


def get_cliente_or_404(user, pk):
    qs = Cliente.objects.para_usuario(user)
    return get_object_or_404(qs, pk=pk)


def aplicar_filtros_clientes(qs, request):
    categoria = request.GET.get('categoria')
    if categoria and categoria != 'todos':
        qs = qs.filter(categoria=categoria)
    elif not categoria or categoria == 'todos':
        if categoria != 'todos':
            qs = qs.exclude(categoria=CategoriaCliente.INATIVO)

    if request.user.is_admin:
        vendedor_id = request.GET.get('vendedor')
        if vendedor_id:
            qs = qs.filter(vendedor_id=vendedor_id)

    for param, choices in (
        ('tipo_cliente', TipoCliente),
        ('modalidade_cliente', ModalidadeCliente),
        ('segmento', SegmentoCliente),
        ('origem_lead', OrigemLead),
        ('status_funil', StatusFunil),
        ('regiao_atuacao', RegiaoAtuacao),
    ):
        val = request.GET.get(param, 'todos')
        if val and val != 'todos':
            qs = qs.filter(**{param: val})

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(nome__icontains=q)
            | Q(cidade__icontains=q)
            | Q(telefone__icontains=q)
            | Q(estado__icontains=q)
            | Q(cep__icontains=q),
        )

    return qs


class ClienteListView(VendedorRequiredMixin, ListView):
    model = Cliente
    template_name = 'clientes/lista.html'
    context_object_name = 'clientes'
    paginate_by = None

    def get_queryset(self):
        qs = get_cliente_queryset(self.request.user)
        qs = aplicar_filtros_clientes(qs, self.request)
        return qs.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        request = self.request

        categoria_param = request.GET.get('categoria')
        context['categoria_atual'] = categoria_param if categoria_param else ''
        context['busca'] = request.GET.get('q', '')
        context['vendedor_atual'] = request.GET.get('vendedor', '')
        context['tipo_cliente_atual'] = request.GET.get('tipo_cliente', 'todos')
        context['modalidade_cliente_atual'] = request.GET.get('modalidade_cliente', 'todos')
        context['segmento_atual'] = request.GET.get('segmento', 'todos')
        context['origem_lead_atual'] = request.GET.get('origem_lead', 'todos')
        context['status_funil_atual'] = request.GET.get('status_funil', 'todos')
        context['regiao_atuacao_atual'] = request.GET.get('regiao_atuacao', 'todos')
        context['filtros_query'] = build_filtros_query(request)
        context['filtros_query_sem_categoria'] = build_filtros_query(request, exclude=('categoria',))

        cliente_id = request.GET.get('id')
        if cliente_id:
            try:
                cliente = get_cliente_or_404(user, cliente_id)
                context['cliente_selecionado'] = cliente
                context['vinculo_form'] = VinculoProdutoForm(cliente=cliente)
                context['produtos_disponiveis_count'] = produtos_disponiveis_para(cliente).count()
            except Http404:
                context['cliente_selecionado'] = None
        elif context['clientes']:
            cliente = context['clientes'][0]
            context['cliente_selecionado'] = cliente
            context['vinculo_form'] = VinculoProdutoForm(cliente=cliente)
            context['produtos_disponiveis_count'] = produtos_disponiveis_para(cliente).count()

        if user.is_admin:
            context['vendedores'] = Usuario.objects.filter(
                papel=Papel.VENDEDOR, ativo=True,
            ).order_by('first_name')

        context['categorias'] = [('todos', 'Todos'), *CategoriaCliente.choices]
        context['tipos_cliente'] = [('todos', 'Todos'), *TipoCliente.choices]
        context['modalidades_cliente'] = [('todos', 'Todos'), *ModalidadeCliente.choices]
        context['segmentos'] = [('todos', 'Todos'), *SegmentoCliente.choices]
        context['origens_lead'] = [('todos', 'Todos'), *OrigemLead.choices]
        context['status_funil_opcoes'] = [('todos', 'Todos'), *StatusFunil.choices]
        context['regioes_atuacao'] = [('todos', 'Todos'), *RegiaoAtuacao.choices]
        context['reativar_form'] = ClienteReativarForm()
        context['tab_ativa'] = request.GET.get('tab', 'dados')

        cliente = context.get('cliente_selecionado')
        if cliente:
            from relacionamento.forms import AtividadeClienteForm
            from relacionamento.models import AtividadeCliente
            from relacionamento.services.resumo_cliente import resumo_comercial_cliente
            context['resumo_comercial'] = resumo_comercial_cliente(cliente)
            context['atividades'] = (
                AtividadeCliente.objects.ativas()
                .filter(cliente=cliente)
                .select_related('usuario', 'produto_relacionado')
                .order_by('-data_criacao')[:50]
            )
            context['atividade_form'] = AtividadeClienteForm(cliente=cliente)

        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            target = self.request.headers.get('HX-Target', '')
            if target == 'produtos-vinculados':
                return ['clientes/partials/produtos_vinculados.html']
            return ['clientes/partials/lista_clientes.html']
        return [self.template_name]


class ClienteCreateView(VendedorRequiredMixin, CreateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/form.html'
    success_url = reverse_lazy('clientes:lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Cliente "{form.instance.nome}" cadastrado com sucesso.')
        self.object = form.save()
        qs = build_filtros_query(self.request)
        url = reverse('clientes:lista') + f'?id={self.object.pk}'
        if qs:
            url += f'&{qs}'
        return redirect(url)


class ClienteUpdateView(VendedorRequiredMixin, UpdateView):
    model = Cliente
    form_class = ClienteForm
    template_name = 'clientes/form.html'

    def get_queryset(self):
        return Cliente.objects.para_usuario(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        qs = build_filtros_query(self.request)
        url = reverse('clientes:lista') + f'?id={self.object.pk}'
        if qs:
            url += f'&{qs}'
        return url

    def form_valid(self, form):
        messages.success(self.request, f'Cliente "{form.instance.nome}" atualizado com sucesso.')
        return super().form_valid(form)


class ClienteInativarView(VendedorRequiredMixin, View):
    def post(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        cliente.categoria = CategoriaCliente.INATIVO
        cliente.save(update_fields=['categoria', 'updated_at'])
        messages.success(request, f'Cliente "{cliente.nome}" inativado.')
        qs = build_filtros_query(request)
        url = reverse('clientes:lista')
        if qs:
            url += f'?{qs}'
        return redirect(url)


class ClienteReativarView(VendedorRequiredMixin, View):
    def post(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        form = ClienteReativarForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Selecione uma categoria válida para reativar.')
            return redirect(reverse('clientes:lista') + f'?id={pk}')

        categoria = form.cleaned_data['categoria']
        validas = {c[0] for c in CATEGORIAS_REATIVACAO}
        if categoria not in validas:
            messages.error(request, 'Categoria inválida.')
            return redirect(reverse('clientes:lista') + f'?id={pk}')

        cliente.categoria = categoria
        cliente.save(update_fields=['categoria', 'updated_at'])
        messages.success(request, f'Cliente "{cliente.nome}" reativado como {cliente.get_categoria_display()}.')
        qs = build_filtros_query(request)
        url = reverse('clientes:lista') + f'?id={pk}'
        if qs:
            url += f'&{qs}'
        return redirect(url)


class ClienteProdutoVincularView(VendedorRequiredMixin, View):
    def post(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        form = VinculoProdutoForm(request.POST, cliente=cliente)
        if form.is_valid():
            try:
                vincular_produto(
                    cliente,
                    form.cleaned_data['produto'],
                    form.cleaned_data.get('observacoes', ''),
                )
                messages.success(request, 'Produto vinculado com sucesso.')
            except ValidationError as exc:
                messages.error(request, exc.messages[0] if exc.messages else str(exc))
        else:
            messages.error(request, 'Selecione um produto válido.')

        if request.headers.get('HX-Request'):
            return render(request, 'clientes/partials/produtos_vinculados.html', {
                'cliente_selecionado': cliente,
                'vinculo_form': VinculoProdutoForm(cliente=cliente),
                'produtos_disponiveis_count': produtos_disponiveis_para(cliente).count(),
            })
        return redirect(reverse('clientes:lista') + f'?id={pk}')


class ClienteProdutoRemoverView(VendedorRequiredMixin, View):
    def post(self, request, pk, vinculo_pk):
        cliente = get_cliente_or_404(request.user, pk)
        vinculo = get_object_or_404(ClienteProduto, pk=vinculo_pk, cliente=cliente)
        desvincular_produto(vinculo)
        messages.success(request, 'Vínculo removido.')

        if request.headers.get('HX-Request'):
            return render(request, 'clientes/partials/produtos_vinculados.html', {
                'cliente_selecionado': cliente,
                'vinculo_form': VinculoProdutoForm(cliente=cliente),
                'produtos_disponiveis_count': produtos_disponiveis_para(cliente).count(),
            })
        return redirect(reverse('clientes:lista') + f'?id={pk}')


class ProdutoListView(VendedorRequiredMixin, ListView):
    model = Produto
    template_name = 'produtos/lista.html'
    context_object_name = 'produtos'
    paginate_by = None

    def get_queryset(self):
        qs = Produto.objects.com_total_clientes()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(categoria__icontains=q))
        tipo = self.request.GET.get('tipo', 'todos')
        if tipo and tipo != 'todos':
            qs = qs.filter(tipo_produto=tipo)
        ativo = self.request.GET.get('ativo', 'todos')
        if ativo == '1':
            qs = qs.filter(ativo=True)
        elif ativo == '0':
            qs = qs.filter(ativo=False)
        return qs.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import TipoProduto
        context['busca'] = self.request.GET.get('q', '')
        context['tipo_atual'] = self.request.GET.get('tipo', 'todos')
        context['ativo_atual'] = self.request.GET.get('ativo', 'todos')
        context['tipos_produto'] = [('todos', 'Todos'), *TipoProduto.choices]
        return context


class ProdutoCreateView(VendedorRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'produtos/form.html'
    success_url = reverse_lazy('produtos:lista')

    def form_valid(self, form):
        messages.success(self.request, f'Produto "{form.instance.nome}" cadastrado.')
        return super().form_valid(form)


class ProdutoUpdateView(VendedorRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'produtos/form.html'
    success_url = reverse_lazy('produtos:lista')

    def form_valid(self, form):
        messages.success(self.request, f'Produto "{form.instance.nome}" atualizado.')
        return super().form_valid(form)
