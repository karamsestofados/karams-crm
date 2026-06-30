from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView as AuthLoginView
from django.contrib.auth.views import LogoutView as AuthLogoutView
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import CreateView, ListView, UpdateView, View

from .forms import (
    ConfiguracaoInicialForm,
    KaramsLoginForm,
    PerfilForm,
    SenhaForm,
    UsuarioCreateForm,
    UsuarioResetSenhaForm,
    UsuarioUpdateForm,
)
from .mixins import AdminRequiredMixin, VendedorRequiredMixin
from .models import Papel, Usuario
from .setup import definir_senha_admin, precisa_configuracao_inicial

from core.forms import RestaurarBackupForm
from core.models import BackupLog, TipoBackup
from core.novidades import dispensar_novidades_popup, marcar_novidades_popup
from extension.models import ExtensionApiToken


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

    def form_valid(self, form):
        marcar_novidades_popup(self.request.session)
        return super().form_valid(form)


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
        context['conquistas'] = self.request.user.conquistas.all()[:20]
        if self.request.user.is_admin:
            context['backup_form'] = RestaurarBackupForm()
            context['ultimo_backup'] = BackupLog.objects.filter(tipo=TipoBackup.BACKUP).first()
        context.update(_contexto_extension_perfil(self.request))
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso.')
        return super().form_valid(form)


@ensure_csrf_cookie
def configuracao_inicial(request):
    if not precisa_configuracao_inicial():
        return redirect('accounts:login')

    form = ConfiguracaoInicialForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        admin = definir_senha_admin(password=form.cleaned_data['password1'])
        login(request, admin)
        marcar_novidades_popup(request.session)
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
        'conquistas': request.user.conquistas.all()[:20],
    }
    if request.user.is_admin:
        ctx['backup_form'] = RestaurarBackupForm()
        ctx['ultimo_backup'] = BackupLog.objects.filter(tipo=TipoBackup.BACKUP).first()
    ctx.update(_contexto_extension_perfil(request))
    return render(request, 'accounts/perfil.html', ctx)


def _contexto_extension_perfil(request):
    token_ativo = (
        ExtensionApiToken.objects.filter(usuario=request.user, ativo=True)
        .order_by('-criado_em')
        .first()
    )
    return {
        'extension_token_ativo': token_ativo,
        'extension_token_plain': request.session.pop('extension_token_plain', None),
        'extension_token_prefix': request.session.get('extension_token_prefix'),
    }


class NovidadesDispensarView(VendedorRequiredMixin, View):
    def post(self, request):
        dispensar_novidades_popup(request.session)
        return redirect(request.META.get('HTTP_REFERER') or reverse('core:dashboard'))


class UsuarioListView(AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'accounts/usuarios_lista.html'
    context_object_name = 'usuarios'

    def get_queryset(self):
        return (
            Usuario.objects.annotate(total_clientes=Count('clientes'))
            .order_by('-date_joined')
        )


class UsuarioCreateView(AdminRequiredMixin, CreateView):
    model = Usuario
    form_class = UsuarioCreateForm
    template_name = 'accounts/usuarios_form.html'
    success_url = reverse_lazy('accounts:usuarios_lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Novo usuário'
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Usuário "{form.instance.username}" criado com sucesso.')
        return super().form_valid(form)


class UsuarioUpdateView(AdminRequiredMixin, UpdateView):
    model = Usuario
    form_class = UsuarioUpdateForm
    template_name = 'accounts/usuarios_form.html'
    success_url = reverse_lazy('accounts:usuarios_lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar usuário'
        context['usuario_editado'] = self.object
        return context

    def form_valid(self, form):
        messages.success(self.request, f'Usuário "{form.instance.username}" atualizado.')
        return super().form_valid(form)


class UsuarioDesativarView(AdminRequiredMixin, View):
    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)

        if usuario.pk == request.user.pk:
            messages.error(request, 'Você não pode desativar sua própria conta.')
            return redirect('accounts:usuarios_lista')

        if usuario.papel == Papel.ADMIN and usuario.ativo:
            admins_ativos = Usuario.objects.filter(papel=Papel.ADMIN, ativo=True).count()
            if admins_ativos <= 1:
                messages.error(request, 'Não é possível desativar o último administrador ativo.')
                return redirect('accounts:usuarios_lista')

        usuario.ativo = not usuario.ativo
        usuario.save(update_fields=['ativo'])
        status = 'ativado' if usuario.ativo else 'desativado'
        messages.success(request, f'Usuário "{usuario.username}" {status}.')
        return redirect('accounts:usuarios_lista')


class UsuarioResetSenhaView(AdminRequiredMixin, View):
    template_name = 'accounts/usuarios_reset_senha.html'

    def get(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        return render(request, self.template_name, {
            'usuario_alvo': usuario,
            'form': UsuarioResetSenhaForm(),
        })

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        form = UsuarioResetSenhaForm(request.POST)
        if form.is_valid():
            usuario.set_password(form.cleaned_data['password1'])
            usuario.save(update_fields=['password'])
            messages.success(request, f'Senha de "{usuario.username}" redefinida.')
            return redirect('accounts:usuarios_lista')
        return render(request, self.template_name, {
            'usuario_alvo': usuario,
            'form': form,
        })
