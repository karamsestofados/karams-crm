from django.contrib.auth.models import AbstractUser
from django.db import models


class Papel(models.TextChoices):
    ADMIN = 'admin', 'Administrador'
    VENDEDOR = 'vendedor', 'Vendedor'


class Tema(models.TextChoices):
    CLARO = 'claro', 'Claro'
    ESCURO = 'escuro', 'Escuro'


class Usuario(AbstractUser):
    papel = models.CharField(
        max_length=20,
        choices=Papel.choices,
        default=Papel.VENDEDOR,
    )
    taxa_comissao_padrao = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.5,
        help_text='Taxa padrão em % (ex: 0.5 = 0,5%)',
    )
    ativo = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    tema = models.CharField(max_length=10, choices=Tema.choices, default=Tema.CLARO)

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'

    @property
    def is_admin(self):
        return self.papel == Papel.ADMIN or self.is_superuser

    @property
    def is_vendedor(self):
        return self.papel == Papel.VENDEDOR

    def __str__(self):
        return self.get_full_name() or self.username
