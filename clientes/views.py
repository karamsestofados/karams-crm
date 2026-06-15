from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from accounts.mixins import VendedorRequiredMixin
from accounts.models import Papel, Usuario

from .forms import ClienteForm
from .models import CategoriaCliente, Cliente


def get_cliente_queryset(user, incluir_inativos=False):
    qs = Cliente.objects.para_usuario(user).select_related('vendedor').prefetch_related(
        'produtos_exclusivos',
    )
    if not incluir_inativos:
        qs = qs.filter(ativo_no_sistema=True)
    return qs


def get_cliente_or_404(user, pk):
    qs = Cliente.objects.para_usuario(user)
    return get_object_or_404(qs, pk=pk)


class ClienteListView(VendedorRequiredMixin, ListView):
    model = Cliente
    template_name = 'clientes/lista.html'
    context_object_name = 'clientes'
    paginate_by = None

    def get_queryset(self):
        incluir_inativos = self.request.GET.get('inativos') == '1'
        qs = get_cliente_queryset(self.request.user, incluir_inativos)

        categoria = self.request.GET.get('categoria', 'todos')
        if categoria and categoria != 'todos':
            qs = qs.filter(categoria=categoria)

        if self.request.user.is_admin:
            vendedor_id = self.request.GET.get('vendedor')
            if vendedor_id:
                qs = qs.filter(vendedor_id=vendedor_id)

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(nome__icontains=q)
                | Q(cidade__icontains=q)
                | Q(telefone__icontains=q)
                | Q(estado__icontains=q),
            )

        return qs.order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['categoria_atual'] = self.request.GET.get('categoria', 'todos')
        context['busca'] = self.request.GET.get('q', '')
        context['inativos'] = self.request.GET.get('inativos') == '1'
        context['vendedor_atual'] = self.request.GET.get('vendedor', '')

        cliente_id = self.request.GET.get('id')
        if cliente_id:
            try:
                context['cliente_selecionado'] = get_cliente_or_404(user, cliente_id)
            except Http404:
                context['cliente_selecionado'] = None
        elif context['clientes']:
            context['cliente_selecionado'] = context['clientes'][0]

        if user.is_admin:
            context['vendedores'] = Usuario.objects.filter(
                papel=Papel.VENDEDOR, ativo=True,
            ).order_by('first_name')

        context['categorias'] = [
            ('todos', 'Todos'),
            *CategoriaCliente.choices,
        ]
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
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
        return redirect(reverse('clientes:lista') + f'?id={self.object.pk}')


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
        return reverse('clientes:lista') + f'?id={self.object.pk}'

    def form_valid(self, form):
        messages.success(self.request, f'Cliente "{form.instance.nome}" atualizado com sucesso.')
        return super().form_valid(form)


class ClienteInativarView(VendedorRequiredMixin, View):
    def post(self, request, pk):
        cliente = get_cliente_or_404(request.user, pk)
        cliente.ativo_no_sistema = False
        cliente.save(update_fields=['ativo_no_sistema', 'updated_at'])
        messages.success(request, f'Cliente "{cliente.nome}" inativado.')
        return redirect('clientes:lista')
