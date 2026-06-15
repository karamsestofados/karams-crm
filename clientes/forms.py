from django import forms

from accounts.models import Papel, Usuario

from .models import CategoriaCliente, Cliente, Produto


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'vendedor', 'nome', 'categoria', 'cidade', 'estado', 'telefone',
            'responsavel', 'instagram', 'endereco', 'data_primeiro_contato',
            'feedback_original', 'produtos_exclusivos', 'ativo_no_sistema',
        ]
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-input'}),
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'cidade': forms.TextInput(attrs={'class': 'form-input'}),
            'estado': forms.TextInput(attrs={'class': 'form-input', 'maxlength': 2}),
            'telefone': forms.TextInput(attrs={'class': 'form-input'}),
            'responsavel': forms.TextInput(attrs={'class': 'form-input'}),
            'instagram': forms.URLInput(attrs={'class': 'form-input'}),
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

        if user and not user.is_admin:
            self.fields['vendedor'].widget = forms.HiddenInput()
            self.fields['vendedor'].initial = user.pk
        else:
            self.fields['vendedor'].queryset = Usuario.objects.filter(
                ativo=True,
            ).order_by('first_name', 'username')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user and not self.user.is_admin:
            instance.vendedor = self.user
        if commit:
            instance.save()
            self.save_m2m()
        return instance
