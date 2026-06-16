from django import forms

from accounts.models import Papel, Usuario

from .models import (
    CategoriaCliente,
    Cliente,
    Produto,
    TipoProduto,
)
from .utils import (
    normalizar_cep,
    normalizar_instagram,
    normalizar_telefone,
    validar_cep,
    validar_telefone,
)

CATEGORIAS_REATIVACAO = [
    (CategoriaCliente.ATIVO, 'Ativo'),
    (CategoriaCliente.ADORMECIDO, 'Adormecido'),
    (CategoriaCliente.PROSPECCAO, 'Prospecção'),
]

CATEGORIAS_FORM = [
    c for c in CategoriaCliente.choices if c[0] != CategoriaCliente.INATIVO
]


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'vendedor', 'nome', 'tipo_cliente', 'segmento', 'modalidade_cliente',
            'categoria', 'status_funil', 'origem_lead', 'regiao_atuacao', 'cidade', 'estado',
            'cep', 'telefone', 'responsavel', 'instagram', 'data_primeiro_contato', 'endereco',
            'feedback_original',
        ]
        widgets = {
            'vendedor': forms.Select(attrs={'class': 'form-input'}),
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'tipo_cliente': forms.Select(attrs={'class': 'form-input'}),
            'segmento': forms.Select(attrs={'class': 'form-input'}),
            'modalidade_cliente': forms.Select(attrs={'class': 'form-input'}),
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
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['estado'].widget.attrs['placeholder'] = 'UF'
        self.fields['categoria'].choices = CATEGORIAS_FORM

        optional_selects = (
            'tipo_cliente', 'segmento', 'modalidade_cliente', 'origem_lead', 'regiao_atuacao',
        )
        for name in optional_selects:
            self.fields[name].required = False
            self.fields[name].empty_label = '— Selecione —'

        self.fields['tipo_cliente'].label = 'Perfil do Cliente'
        self.fields['modalidade_cliente'].label = 'Tipo Cliente'
        self.fields['vendedor'].label = 'Vendedor Responsável'

        if self.instance and self.instance.pk and self.instance.categoria == CategoriaCliente.INATIVO:
            self.fields.pop('categoria', None)

        if user and not user.is_admin:
            self.fields['vendedor'].widget = forms.HiddenInput()
            self.fields['vendedor'].initial = user.pk
        else:
            self.fields['vendedor'].queryset = Usuario.objects.filter(
                papel=Papel.VENDEDOR,
                ativo=True,
            ).order_by('first_name', 'username')

    def clean_categoria(self):
        categoria = self.cleaned_data.get('categoria')
        if categoria == CategoriaCliente.INATIVO:
            raise forms.ValidationError(
                'Use o botão Inativar na ficha do cliente para definir como Inativo.'
            )
        return categoria

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
        return instance


class ClienteReativarForm(forms.Form):
    categoria = forms.ChoiceField(
        choices=CATEGORIAS_REATIVACAO,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Nova categoria',
    )


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'categoria', 'tipo_produto', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-input'}),
            'descricao': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'categoria': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Estofados, Poltronas...'}),
            'tipo_produto': forms.Select(attrs={'class': 'form-input'}),
            'ativo': forms.CheckboxInput(),
        }


class VinculoProdutoForm(forms.Form):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.none(),
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Produto',
    )
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 2, 'placeholder': 'Observações opcionais'}),
        label='Observações',
    )

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        if cliente:
            from .services.produtos import produtos_disponiveis_para
            self.fields['produto'].queryset = produtos_disponiveis_para(cliente)
