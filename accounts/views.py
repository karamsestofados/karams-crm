from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import ConfiguracaoInicialForm, KaramsLoginForm, PerfilForm, SenhaForm
from .mixins import VendedorRequiredMixin
from .models import Usuario
from .setup import definir_senha_admin, precisa_configuracao_inicial

from core.forms import RestaurarBackupForm
from core.models import BackupLog, TipoBackup


class LoginView(AuthLoginView):
    template_name = 'accounts/login.html'
    authentication_form = KaramsLoginForm
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if precisa_configuracao_inicial():
            return redirect('accounts:configuracao_inicial')
        return super().dispatch(request, *args, **kwargs)

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
        if self.request.user.is_admin:
            context['backup_form'] = RestaurarBackupForm()
            context['ultimo_backup'] = BackupLog.objects.filter(tipo=TipoBackup.BACKUP).first()
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso.')
        return super().form_valid(form)


def configuracao_inicial(request):
    if not precisa_configuracao_inicial():
        return redirect('accounts:login')

    form = ConfiguracaoInicialForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        admin = definir_senha_admin(password=form.cleaned_data['password1'])
        login(request, admin)
        messages.success(request, 'Senha definida. Bem-vindo ao Karams CRM.')
        return redirect('core:dashboard')

    return render(request, 'accounts/configuracao_inicial.html', {'form': form})


def alterar_senha(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    form = SenhaForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Senha alterada com sucesso.')
        return redirect('accounts:perfil')
    ctx = {
        'form': PerfilForm(instance=request.user),
        'senha_form': form,
    }
    if request.user.is_admin:
        ctx['backup_form'] = RestaurarBackupForm()
        ctx['ultimo_backup'] = BackupLog.objects.filter(tipo=TipoBackup.BACKUP).first()
    return render(request, 'accounts/perfil.html', ctx)
