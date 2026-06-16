from django import forms

MAX_BACKUP_SIZE = 100 * 1024 * 1024  # 100 MB


class RestaurarBackupForm(forms.Form):
    arquivo = forms.FileField(
        label='Arquivo de backup',
        help_text='Selecione o arquivo .karamsbackup.zip gerado anteriormente.',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input',
            'accept': '.zip,.karamsbackup.zip',
        }),
    )

    confirmar = forms.BooleanField(
        label='Entendo que todos os dados atuais serão substituídos',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        if arquivo.size > MAX_BACKUP_SIZE:
            raise forms.ValidationError('Arquivo muito grande (máximo 100 MB).')
        name = (arquivo.name or '').lower()
        if not (name.endswith('.zip') or name.endswith('.karamsbackup.zip')):
            raise forms.ValidationError('Envie um arquivo .karamsbackup.zip válido.')
        return arquivo
