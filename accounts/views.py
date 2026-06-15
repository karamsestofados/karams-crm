from django.contrib import messages
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import KaramsLoginForm, PerfilForm, SenhaForm
from .mixins import VendedorRequiredMixin
from .models import Usuario


class LoginView(AuthLoginView):
    template_name = 'accounts/login.html'
    authentication_form = KaramsLoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('core:dashboard')


class LogoutView(AuthLogoutView):
    next_page = reverse_lazy('accounts:login')


class PerfilView(VendedorRequiredMixin, UpdateView):
    model = Usuario
    form_class = PerfilForm
    template_name = 'accounts/perfil.html'
    success_url = reverse_lazy('accounts:perfil')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['senha_form'] = SenhaForm(self.request.user)
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso.')
        return super().form_valid(form)


def alterar_senha(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    form = SenhaForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Senha alterada com sucesso.')
        return redirect('accounts:perfil')
    return render(request, 'accounts/perfil.html', {
        'form': PerfilForm(instance=request.user),
        'senha_form': form,
    })
