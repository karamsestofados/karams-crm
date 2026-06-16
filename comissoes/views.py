from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView, View

from accounts.mixins import AdminRequiredMixin

from .forms import MetaMensalForm
from .models import MetaMensal


class MetaListView(AdminRequiredMixin, ListView):
    model = MetaMensal
    template_name = 'comissoes/metas_lista.html'
    context_object_name = 'metas'

    def get_queryset(self):
        return MetaMensal.objects.select_related('vendedor').order_by('-ano', '-mes', 'vendedor__first_name')


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
