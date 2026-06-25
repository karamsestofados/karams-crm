from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views import View

from accounts.mixins import VendedorRequiredMixin

from .auth import extension_token_required
from .models import ExtensionApiToken
from .services.contexto_whatsapp import montar_contexto_extension


@method_decorator(extension_token_required, name='dispatch')
class ExtensionMeView(View):
    def get(self, request):
        user = request.extension_user
        return JsonResponse({
            'id': user.pk,
            'username': user.username,
            'nome': user.get_full_name() or user.username,
            'papel': user.papel,
            'is_admin': user.is_admin,
        })


@method_decorator(extension_token_required, name='dispatch')
class ExtensionContextoView(View):
    def get(self, request):
        telefone = request.GET.get('telefone', '').strip()
        payload = montar_contexto_extension(request, request.extension_user, telefone)
        return JsonResponse(payload)


class ExtensionTokenGerarView(VendedorRequiredMixin, View):
    def post(self, request):
        token_obj, raw_token = ExtensionApiToken.gerar_para_usuario(request.user)
        request.session['extension_token_plain'] = raw_token
        request.session['extension_token_prefix'] = token_obj.prefixo
        messages.success(
            request,
            'Token gerado. Copie agora — ele não será exibido novamente.',
        )
        return redirect('accounts:perfil')


class ExtensionTokenRevogarView(VendedorRequiredMixin, View):
    def post(self, request):
        ExtensionApiToken.objects.filter(usuario=request.user, ativo=True).update(ativo=False)
        request.session.pop('extension_token_plain', None)
        request.session.pop('extension_token_prefix', None)
        messages.success(request, 'Token da extensão revogado.')
        return redirect('accounts:perfil')
