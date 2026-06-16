from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Papel, Tema, Usuario


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

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.ativo:
            raise ValidationError(
                'Conta desativada. Entre em contato com o administrador.',
                code='inactive',
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
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Nova senha',
            'autofocus': True,
        }),
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Repita a senha',
        }),
    )

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


_FORM_INPUT = {'class': 'form-input'}


class UsuarioCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs=_FORM_INPUT),
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs=_FORM_INPUT),
    )

    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'papel', 'ativo')
        widgets = {
            'username': forms.TextInput(attrs=_FORM_INPUT),
            'first_name': forms.TextInput(attrs=_FORM_INPUT),
            'last_name': forms.TextInput(attrs=_FORM_INPUT),
            'email': forms.EmailInput(attrs=_FORM_INPUT),
            'papel': forms.Select(attrs=_FORM_INPUT),
            'ativo': forms.CheckboxInput(),
        }

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'As senhas não coincidem.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if user.papel == Papel.VENDEDOR:
            user.is_staff = False
            user.is_superuser = False
        elif user.papel == Papel.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class UsuarioUpdateForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'papel', 'ativo')
        widgets = {
            'username': forms.TextInput(attrs=_FORM_INPUT),
            'first_name': forms.TextInput(attrs=_FORM_INPUT),
            'last_name': forms.TextInput(attrs=_FORM_INPUT),
            'email': forms.EmailInput(attrs=_FORM_INPUT),
            'papel': forms.Select(attrs=_FORM_INPUT),
            'ativo': forms.CheckboxInput(),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if user.papel == Papel.VENDEDOR:
            user.is_staff = False
            user.is_superuser = False
        elif user.papel == Papel.ADMIN:
            user.is_staff = True
        if commit:
            user.save()
        return user


class UsuarioResetSenhaForm(forms.Form):
    password1 = forms.CharField(
        label='Nova senha',
        widget=forms.PasswordInput(attrs=_FORM_INPUT),
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput(attrs=_FORM_INPUT),
    )

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'As senhas não coincidem.')
        return cleaned

