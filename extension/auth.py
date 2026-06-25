import json
from functools import wraps

from django.http import JsonResponse

from extension.models import ExtensionApiToken


def _extrair_bearer_token(request):
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return request.GET.get('token', '').strip() or None


def extension_token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        raw = _extrair_bearer_token(request)
        if not raw:
            return JsonResponse({'erro': 'Token não informado.'}, status=401)
        usuario = ExtensionApiToken.autenticar(raw)
        if not usuario:
            return JsonResponse({'erro': 'Token inválido ou revogado.'}, status=401)
        request.extension_user = usuario
        return view_func(request, *args, **kwargs)

    return wrapper
