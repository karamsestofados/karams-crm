from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserChangeForm

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
