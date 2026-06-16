from django import forms

from accounts.models import Papel, Usuario

from .models import Cliente, Produto
from .utils import (
    normalizar_cep,
    normalizar_instagram,
    normalizar_telefone,
    validar_cep,
    validar_telefone,
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'vendedor', 'nome', 'tipo_cliente', 'segmento', 'categoria', 'status_funil',
            'origem_lead', 'regiao_atuacao', 'cidade', 'estado', 'cep', 'telefone',
            'responsavel', 'instagram', 'data_primeiro_contato', 'endereco',
            'feedback_original', 'produtos_exclusivos', 'ativo_no_sistema',
        ]
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-input'}),
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'tipo_cliente': forms.Select(attrs={'class': 'form-input'}),
            'segmento': forms.Select(attrs={'class': 'form-input'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'status_funil': forms.Select(attrs={'class': 'form-input'}),
            'origem_lead': forms.Select(attrs={'class': 'form-input'}),
            'regiao_atuacao': forms.Select(attrs={'class': 'form-input'}),
            'cidade': forms.TextInput(attrs={'class': 'form-input'}),
            'estado': forms.TextInput(attrs={'class': 'form-input', 'maxlength': 2}),
            'cep': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '99999-999',
                'data-mask': 'cep',
                'maxlength': 9,
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '(99) 99999-9999',
                'data-mask': 'telefone',
                'maxlength': 15,
            }),
            'responsavel': forms.TextInput(attrs={'class': 'form-input'}),
            'instagram': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '@usuario',
            }),
            'endereco': forms.Textarea(attrs={'class': 'form-input', 'rows': 2}),
            'data_primeiro_contato': forms.DateInput(
                attrs={'class': 'form-input', 'type': 'date'},
            ),
            'feedback_original': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'produtos_exclusivos': forms.CheckboxSelectMultiple(),
            'ativo_no_sistema': forms.CheckboxInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['produtos_exclusivos'].queryset = Produto.objects.order_by('nome')
        self.fields['estado'].widget.attrs['placeholder'] = 'UF'

        optional_selects = (
            'tipo_cliente', 'segmento', 'origem_lead', 'regiao_atuacao',
        )
        for name in optional_selects:
            self.fields[name].required = False
            self.fields[name].empty_label = '— Selecione —'

        if user and not user.is_admin:
            self.fields['vendedor'].widget = forms.HiddenInput()
            self.fields['vendedor'].initial = user.pk
        else:
            self.fields['vendedor'].queryset = Usuario.objects.filter(
                ativo=True,
            ).order_by('first_name', 'username')

    def clean_cep(self):
        cep = normalizar_cep(self.cleaned_data.get('cep', ''))
        if cep and not validar_cep(cep):
            raise forms.ValidationError('CEP inválido. Use o formato 99999-999.')
        return cep

    def clean_telefone(self):
        telefone = normalizar_telefone(self.cleaned_data.get('telefone', ''))
        if telefone and not validar_telefone(telefone):
            raise forms.ValidationError('Telefone inválido. Use (99) 99999-9999 ou (99) 9999-9999.')
        return telefone

    def clean_instagram(self):
        return normalizar_instagram(self.cleaned_data.get('instagram', ''))

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not self.user.is_admin:
            instance.vendedor = self.user
        if commit:
            instance.save()
            self.save_m2m()
        return instance
