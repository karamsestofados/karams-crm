from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from accounts.mixins import AdminRequiredMixin
from accounts.models import Papel, Usuario

from .forms import MetaMensalForm
from .models import MetaMensal


class MetaListView(AdminRequiredMixin, ListView):
    model = MetaMensal
    template_name = 'comissoes/metas_lista.html'
    context_object_name = 'metas'

    def get_queryset(self):
        qs = MetaMensal.objects.select_related('vendedor').order_by('-ano', '-mes', 'vendedor__first_name')
        mes = self.request.GET.get('mes')
        ano = self.request.GET.get('ano')
        vendedor = self.request.GET.get('vendedor')
        ativo = self.request.GET.get('ativo')

        if mes:
            try:
                qs = qs.filter(mes=int(mes))
            except ValueError:
                pass
        if ano:
            try:
                qs = qs.filter(ano=int(ano))
            except ValueError:
                pass
        if vendedor == 'equipe':
            qs = qs.filter(vendedor__isnull=True)
        elif vendedor:
            try:
                qs = qs.filter(vendedor_id=int(vendedor))
            except ValueError:
                pass
        if ativo == '1':
            qs = qs.filter(ativo=True)
        elif ativo == '0':
            qs = qs.filter(ativo=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtros'] = {
            'mes': self.request.GET.get('mes', ''),
            'ano': self.request.GET.get('ano', ''),
            'vendedor': self.request.GET.get('vendedor', ''),
            'ativo': self.request.GET.get('ativo', ''),
        }
        context['vendedores'] = Usuario.objects.filter(
            papel=Papel.VENDEDOR, ativo=True,
        ).order_by('first_name')
        return context


class MetaCreateView(AdminRequiredMixin, CreateView):
    model = MetaMensal
    form_class = MetaMensalForm
    template_name = 'comissoes/metas_form.html'
    success_url = reverse_lazy('comissoes:metas_lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Nova meta comercial'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Meta comercial criada com sucesso.')
        return super().form_valid(form)


class MetaUpdateView(AdminRequiredMixin, UpdateView):
    model = MetaMensal
    form_class = MetaMensalForm
    template_name = 'comissoes/metas_form.html'
    success_url = reverse_lazy('comissoes:metas_lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar meta comercial'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Meta comercial atualizada.')
        return super().form_valid(form)


class MetaDesativarView(AdminRequiredMixin, View):
    def post(self, request, pk):
        meta = get_object_or_404(MetaMensal, pk=pk)
        meta.ativo = not meta.ativo
        meta.save(update_fields=['ativo'])
        status = 'ativada' if meta.ativo else 'desativada'
        messages.success(request, f'Meta {status}.')
        return redirect('comissoes:metas_lista')
