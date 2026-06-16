from django import forms

from accounts.models import Papel, Usuario

from .models import MetaMensal

_FORM_INPUT = {'class': 'form-input'}


class MetaMensalForm(forms.ModelForm):
    class Meta:
        model = MetaMensal
        fields = (
            'vendedor', 'mes', 'ano',
            'meta_contatos', 'meta_clientes_novos', 'meta_propostas',
            'meta_visitas', 'meta_vendas', 'observacoes', 'ativo',
        )
        widgets = {
            'vendedor': forms.Select(attrs=_FORM_INPUT),
            'mes': forms.NumberInput(attrs={**_FORM_INPUT, 'min': 1, 'max': 12}),
            'ano': forms.NumberInput(attrs={**_FORM_INPUT, 'min': 2020, 'max': 2100}),
            'meta_contatos': forms.NumberInput(attrs=_FORM_INPUT),
            'meta_clientes_novos': forms.NumberInput(attrs=_FORM_INPUT),
            'meta_propostas': forms.NumberInput(attrs=_FORM_INPUT),
            'meta_visitas': forms.NumberInput(attrs=_FORM_INPUT),
            'meta_vendas': forms.NumberInput(attrs={**_FORM_INPUT, 'step': '0.01'}),
            'observacoes': forms.Textarea(attrs={**_FORM_INPUT, 'rows': 3}),
            'ativo': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vendedor'].queryset = Usuario.objects.filter(
            papel=Papel.VENDEDOR, ativo=True,
        ).order_by('first_name', 'username')
        self.fields['vendedor'].required = False
        self.fields['vendedor'].empty_label = 'Equipe (geral)'
        self.fields['meta_vendas'].label = 'Meta de Vendas (R$)'
        self.fields['meta_contatos'].label = 'Giro de Carteira (%)'

    def clean(self):
        cleaned = super().clean()
        vendedor = cleaned.get('vendedor')
        mes = cleaned.get('mes')
        ano = cleaned.get('ano')
        if not vendedor and mes and ano:
            if MetaMensal.objects.filter(
                vendedor__isnull=False, mes=mes, ano=ano, ativo=True,
            ).exists():
                raise forms.ValidationError(
                    'A meta da equipe é calculada automaticamente pela soma dos vendedores. '
                    'Cadastre metas individuais ou remova as existentes para usar meta manual.'
                )
        if mes and ano:
            qs = MetaMensal.objects.filter(vendedor=vendedor, mes=mes, ano=ano)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                alvo = vendedor.get_full_name() if vendedor else 'Equipe'
                raise forms.ValidationError(
                    f'Já existe uma meta para {alvo} em {mes:02d}/{ano}.'
                )
        return cleaned
