from django import forms
import json

from clientes.models import MotivoPerda, Produto

from .models import (
    AtividadeCliente,
    HumorCliente,
    ProximaAcao,
    Resultado,
    TipoContato,
)
from .services.external_calendar.policy import (
    HORA_PADRAO_FOLLOWUP,
    normalize_hora,
    validar_followup_obrigatorio,
)

_FORM_INPUT = {'class': 'form-input'}


def _apply_followup_clean(cleaned, form):
    proxima = cleaned.get('proxima_acao')
    data = cleaned.get('data_proxima_acao')
    resultado = cleaned.get('resultado')

    msg = validar_followup_obrigatorio(resultado, proxima, data)
    if msg:
        form.add_error(None, msg)

    if proxima and proxima != ProximaAcao.SEM_ACAO and not data:
        form.add_error('data_proxima_acao', 'Informe a data da próxima ação.')

    if proxima == ProximaAcao.SEM_ACAO:
        cleaned['data_proxima_acao'] = None
        cleaned['hora_proxima_acao'] = None
    elif data and not cleaned.get('hora_proxima_acao'):
        cleaned['hora_proxima_acao'] = HORA_PADRAO_FOLLOWUP

    if cleaned.get('hora_proxima_acao'):
        cleaned['hora_proxima_acao'] = normalize_hora(cleaned['hora_proxima_acao'])

    return cleaned


class AtividadeClienteForm(forms.ModelForm):
    valor_venda = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        label='Valor da Venda (R$)',
        widget=forms.NumberInput(attrs={**_FORM_INPUT, 'step': '0.01', 'placeholder': '0,00'}),
    )
    motivo_perda = forms.ChoiceField(
        required=False,
        choices=[('', '— Selecione —')] + list(MotivoPerda.choices),
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Motivo da perda',
    )
    motivo_perda_detalhe = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Descreva se escolheu Outro'}),
        label='Detalhe do motivo',
    )

    class Meta:
        model = AtividadeCliente
        fields = [
            'tipo_contato', 'assunto', 'resumo', 'resultado', 'humor_cliente',
            'produtos_relacionados', 'proxima_acao', 'data_proxima_acao', 'hora_proxima_acao',
        ]
        widgets = {
            'tipo_contato': forms.Select(attrs={'class': 'form-input'}),
            'assunto': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Linha Toscana'}),
            'resumo': forms.Textarea(attrs={'class': 'form-input', 'rows': 4, 'placeholder': 'Descreva a interação...'}),
            'resultado': forms.Select(attrs={'class': 'form-input'}),
            'humor_cliente': forms.Select(attrs={'class': 'form-input'}),
            'produtos_relacionados': forms.MultipleHiddenInput(),
            'proxima_acao': forms.Select(attrs={'class': 'form-input'}),
            'data_proxima_acao': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'hora_proxima_acao': forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        }

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['humor_cliente'].required = False
        self.fields['humor_cliente'].empty_label = '— Selecione —'
        self.fields['produtos_relacionados'].required = False
        self.fields['produtos_relacionados'].queryset = Produto.objects.ativos().order_by('nome')
        self.fields['produtos_relacionados'].label = 'Produtos relacionados'
        self.produtos_catalogo = list(
            Produto.objects.ativos().order_by('nome').values('id', 'nome', 'tipo_produto')
        )
        self._produtos_selecionados_iniciais()
        self.produtos_catalogo_json = json.dumps(self.produtos_catalogo, ensure_ascii=False)
        self.produtos_selecionados_json = json.dumps(self.produtos_selecionados)
        self.fields['data_proxima_acao'].required = False
        self.fields['hora_proxima_acao'].required = False

    def _produtos_selecionados_iniciais(self):
        if self.is_bound:
            if hasattr(self.data, 'getlist'):
                raw = self.data.getlist('produtos_relacionados')
            else:
                raw = self.data.get('produtos_relacionados', [])
                if not isinstance(raw, list):
                    raw = [raw] if raw else []
            self.produtos_selecionados = [int(pk) for pk in raw if pk]
        elif self.instance.pk:
            self.produtos_selecionados = list(
                self.instance.produtos_relacionados.values_list('pk', flat=True)
            )
        else:
            self.produtos_selecionados = []

    def clean(self):
        cleaned = super().clean()
        cleaned = _apply_followup_clean(cleaned, self)
        resumo = cleaned.get('resumo', '')
        if not resumo or not resumo.strip():
            self.add_error('resumo', 'O resumo é obrigatório.')
        resultado = cleaned.get('resultado')
        valor_venda = cleaned.get('valor_venda')
        if resultado == Resultado.PEDIDO_FECHADO and (valor_venda is None or valor_venda <= 0):
            self.add_error('valor_venda', 'Informe o valor da venda para pedido fechado.')
        if resultado == Resultado.SEM_INTERESSE:
            motivo = cleaned.get('motivo_perda')
            if not motivo:
                self.add_error('motivo_perda', 'Informe o motivo da perda.')
            elif motivo == MotivoPerda.OUTRO and not (cleaned.get('motivo_perda_detalhe') or '').strip():
                self.add_error('motivo_perda_detalhe', 'Descreva o motivo.')
        return cleaned


class AtividadeClienteEditForm(AtividadeClienteForm):
    """Formulário de edição — sem motivo_perda (alteração de funil legado)."""

    class Meta(AtividadeClienteForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['valor_venda'].initial = self.instance.valor_venda
        self.fields.pop('motivo_perda', None)
        self.fields.pop('motivo_perda_detalhe', None)

    def clean(self):
        cleaned = super(forms.ModelForm, self).clean()
        cleaned = _apply_followup_clean(cleaned, self)
        resumo = cleaned.get('resumo', '')
        if not resumo or not resumo.strip():
            self.add_error('resumo', 'O resumo é obrigatório.')
        resultado = cleaned.get('resultado')
        valor_venda = cleaned.get('valor_venda')
        if resultado == Resultado.PEDIDO_FECHADO and (valor_venda is None or valor_venda <= 0):
            self.add_error('valor_venda', 'Informe o valor da venda para pedido fechado.')
        return cleaned


class ConcluirFollowupForm(forms.Form):
    resumo = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Registre tudo que foi conversado...'}),
        label='Resumo',
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
    hora_proxima_acao = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={'class': 'form-input', 'type': 'time'}),
        label='Hora',
    )
    valor_venda = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        label='Valor da Venda (R$)',
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'placeholder': '0,00'}),
    )

    def clean(self):
        cleaned = super().clean()
        cleaned = _apply_followup_clean(cleaned, self)
        resultado = cleaned.get('resultado')
        valor_venda = cleaned.get('valor_venda')
        if resultado == Resultado.PEDIDO_FECHADO and (valor_venda is None or valor_venda <= 0):
            self.add_error('valor_venda', 'Informe o valor da venda para pedido fechado.')
        return cleaned


class InteracaoGlobalForm(AtividadeClienteForm):
    cliente = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='Cliente',
    )

    def __init__(self, *args, user=None, cliente=None, **kwargs):
        super().__init__(*args, cliente=cliente, **kwargs)
        from clientes.models import Cliente

        self.fields['cliente'].queryset = Cliente.objects.para_usuario(user).ativos().order_by('nome')
        if cliente:
            self.fields['cliente'].initial = cliente.pk
        if 'tipo_contato' in self.initial:
            self.fields['tipo_contato'].initial = self.initial['tipo_contato']
