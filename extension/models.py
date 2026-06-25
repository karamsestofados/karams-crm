import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


class ExtensionApiToken(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='extension_tokens',
    )
    prefixo = models.CharField(max_length=16, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'token da extensão'
        verbose_name_plural = 'tokens da extensão'

    def __str__(self):
        return f'{self.prefixo}… ({self.usuario})'

    @classmethod
    def gerar_para_usuario(cls, usuario):
        cls.objects.filter(usuario=usuario, ativo=True).update(ativo=False)
        raw = secrets.token_urlsafe(32)
        full_token = f'karams_{raw}'
        token = cls.objects.create(
            usuario=usuario,
            prefixo=full_token[:12],
            token_hash=_hash_token(full_token),
        )
        return token, full_token

    @classmethod
    def autenticar(cls, raw_token: str):
        if not raw_token or not raw_token.startswith('karams_'):
            return None
        token_hash = _hash_token(raw_token.strip())
        token = (
            cls.objects.select_related('usuario')
            .filter(token_hash=token_hash, ativo=True, usuario__ativo=True)
            .first()
        )
        if not token:
            return None
        ExtensionApiToken.objects.filter(pk=token.pk).update(ultimo_uso=timezone.now())
        return token.usuario
