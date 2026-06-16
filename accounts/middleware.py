from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from core.audit import clear_current_user, set_current_user


class ConfiguracaoInicialMiddleware:
    """Redireciona para a configuração inicial enquanto não houver administrador."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from accounts.setup import precisa_configuracao_inicial

        if precisa_configuracao_inicial() and not self._rota_liberada(request):
            return redirect('accounts:configuracao_inicial')
        return self.get_response(request)

    def _rota_liberada(self, request):
        from django.conf import settings

        path = request.path
        setup_path = reverse('accounts:configuracao_inicial')
        if path == setup_path or path.startswith(settings.STATIC_URL):
            return True
        return False


class CurrentUserMiddleware:
    """Disponibiliza o usuário autenticado para auditoria nos models."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            set_current_user(request.user)
        try:
            return self.get_response(request)
        finally:
            clear_current_user()


class UsuarioAtivoMiddleware:
    """Encerra sessão de usuários desativados."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated and not user.ativo:
            logout(request)
            from django.contrib import messages

            messages.error(request, 'Sua conta foi desativada. Entre em contato com o administrador.')
            return redirect('accounts:login')
        return self.get_response(request)


class AdminSiteAccessMiddleware:
    """Bloqueia vendedores no Django Admin (/admin/)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if not request.user.is_authenticated:
                return self.get_response(request)
            if not request.user.is_admin:
                raise PermissionDenied('Acesso não autorizado.')
        return self.get_response(request)
