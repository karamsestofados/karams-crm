from django import forms

from clientes.models import Produto

from .models import (
    AtividadeCliente,
    HumorCliente,
    ProximaAcao,
    Resultado,
    TipoContato,
)


class AtividadeClienteForm(forms.ModelForm):
    class Meta:
        model = AtividadeCliente
        fields = [
            'tipo_contato', 'assunto', 'resumo', 'resultado', 'humor_cliente',
            'produto_relacionado', 'proxima_acao', 'data_proxima_acao',
        ]
        widgets = {
            'tipo_contato': forms.Select(attrs={'class': 'form-input'}),
            'assunto': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Linha Toscana'}),
            'resumo': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Descreva a interação...'}),
            'resultado': forms.Select(attrs={'class': 'form-input'}),
            'humor_cliente': forms.Select(attrs={'class': 'form-input'}),
            'produto_relacionado': forms.Select(attrs={'class': 'form-input'}),
            'proxima_acao': forms.Select(attrs={'class': 'form-input'}),
            'data_proxima_acao': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['humor_cliente'].required = False
        self.fields['humor_cliente'].empty_label = '— Selecione —'
        self.fields['produto_relacionado'].required = False
        self.fields['produto_relacionado'].empty_label = '— Nenhum —'
        self.fields['produto_relacionado'].queryset = Produto.objects.ativos().order_by('nome')
        self.fields['data_proxima_acao'].required = False

    def clean(self):
        cleaned = super().clean()
        proxima = cleaned.get('proxima_acao')
        data = cleaned.get('data_proxima_acao')
        if proxima and proxima != ProximaAcao.SEM_ACAO and not data:
            self.add_error('data_proxima_acao', 'Informe a data da próxima ação.')
        if proxima == ProximaAcao.SEM_ACAO:
            cleaned['data_proxima_acao'] = None
        resumo = cleaned.get('resumo', '')
        if not resumo or not resumo.strip():
            self.add_error('resumo', 'O resumo é obrigatório.')
        return cleaned


class ConcluirFollowupForm(forms.Form):
    resumo = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'O que aconteceu?'}),
        label='O que aconteceu?',
    )
    tipo_contato = forms.ChoiceField(
        choices=TipoContato.choices,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Tipo de contato',
    )
    resultado = forms.ChoiceField(
        choices=Resultado.choices,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Resultado',
    )
    proxima_acao = forms.ChoiceField(
        choices=ProximaAcao.choices,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Próxima ação',
        initial=ProximaAcao.SEM_ACAO,
    )
    data_proxima_acao = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        label='Data próxima ação',
    )

    def clean(self):
        cleaned = super().clean()
        proxima = cleaned.get('proxima_acao')
        data = cleaned.get('data_proxima_acao')
        if proxima and proxima != ProximaAcao.SEM_ACAO and not data:
            self.add_error('data_proxima_acao', 'Informe a data da próxima ação.')
        return cleaned
