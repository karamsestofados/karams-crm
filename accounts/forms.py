from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Tema, Usuario


class KaramsLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Usuário',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Senha',
        }),
    )


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email', 'tema', 'taxa_comissao_padrao')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'tema': forms.Select(attrs={'class': 'form-input'}),
            'taxa_comissao_padrao': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
        }


class SenhaForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-input'


class ConfiguracaoInicialForm(forms.Form):
    username = forms.CharField(
        label='Usuário administrador',
        initial='admin',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'autofocus': True}),
    )
    first_name = forms.CharField(
        label='Nome',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    last_name = forms.CharField(
        label='Sobrenome',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-input'}),
    )
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={'class': 'form-input'}),
    )
    meta_contatos = forms.IntegerField(
        label='Meta mensal de contatos (equipe)',
        initial=settings.METAS_PADRAO_CONTATOS,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-input'}),
    )
    meta_vendas = forms.DecimalField(
        label='Meta mensal de vendas R$ (equipe)',
        initial=settings.METAS_PADRAO_VENDAS,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Este usuário já existe.')
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            try:
                validate_password(password)
            except ValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'As senhas não coincidem.')
        return cleaned
