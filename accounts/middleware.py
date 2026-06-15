from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from accounts.setup import precisa_configuracao_inicial


class ConfiguracaoInicialMiddleware:
    """Redireciona para a configuração inicial enquanto não houver administrador."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if precisa_configuracao_inicial() and not self._rota_liberada(request):
            return redirect('accounts:configuracao_inicial')
        return self.get_response(request)

    def _rota_liberada(self, request):
        path = request.path
        setup_path = reverse('accounts:configuracao_inicial')
        if path == setup_path or path.startswith(settings.STATIC_URL):
            return True
        return False
