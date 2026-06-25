import json
import zipfile
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TransactionTestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from core.services.backup import (
    BACKUP_FORMAT_VERSION,
    _manifest,
    _normalizar_fixture_backup,
    restaurar_arquivo_backup,
)
from powerup.services.context import build_powerup_context
from relacionamento.models import AtividadeCliente


def _user_backup_path():
    return Path(
        r'c:\Users\T.I E MANUTENÇÃO\Downloads\karams-backup-2026-06-23-102508.karamsbackup.zip',
    )


def _backup_path_2026_06_24():
    return Path(
        r'c:\Users\T.I E MANUTENÇÃO\Downloads\karams-backup-2026-06-24-122147.karamsbackup.zip',
    )


def _backup_path_2026_06_25():
    return Path(
        r'c:\Users\T.I E MANUTENÇÃO\Downloads\karams-backup-2026-06-25-123247.karamsbackup.zip',
    )


class BackupRestoreIntegrationTest(TransactionTestCase):
    def test_manifest_inclui_features_powerup(self):
        manifest = _manifest()
        self.assertEqual(manifest['format_version'], BACKUP_FORMAT_VERSION)
        self.assertIn('motivo_perda', manifest['features'])
        self.assertIn('powerup', manifest['features'])

    def test_restore_backup_usuario_powerup_ok(self):
        path = _user_backup_path()
        if not path.is_file():
            self.skipTest('Arquivo de backup do usuário não disponível neste ambiente.')

        uploaded = SimpleUploadedFile(
            path.name,
            path.read_bytes(),
            content_type='application/zip',
        )
        restaurar_arquivo_backup(uploaded)

        self.assertEqual(Cliente.objects.count(), 73)
        self.assertEqual(Usuario.objects.filter(papel=Papel.VENDEDOR).count(), 2)

        admin = Usuario.objects.get(username='admin')
        from django.test import RequestFactory
        req = RequestFactory().get('/powerup/')
        req.user = admin
        ctx = build_powerup_context(req)

        self.assertEqual(len(ctx['funil']), 4)
        self.assertEqual(len(ctx['conversao_vendedores']), 2)
        self.assertIn('motivo_perda', ctx)

    def test_restore_backup_24_06_historico_visivel_admin(self):
        path = _backup_path_2026_06_24()
        if not path.is_file():
            self.skipTest('Backup 2026-06-24 não disponível neste ambiente.')

        uploaded = SimpleUploadedFile(
            path.name,
            path.read_bytes(),
            content_type='application/zip',
        )
        restaurar_arquivo_backup(uploaded)

        self.assertEqual(AtividadeCliente.objects.ativas().count(), 64)

        admin = Usuario.objects.get(username='admin')
        cliente = Cliente.objects.filter(
            atividades__isnull=False,
        ).distinct().first()
        self.assertIsNotNone(cliente)

        client = Client()
        client.force_login(admin)
        response = client.get(
            reverse('clientes:lista') + f'?id={cliente.pk}&tab=historico',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'timeline-card')
        self.assertNotContains(
            response,
            'Nenhuma interação registrada ainda.',
        )

    def test_normalizar_produto_relacionado_legado(self):
        payload = [{
            'model': 'relacionamento.atividadecliente',
            'pk': 1,
            'fields': {
                'cliente': 1,
                'usuario': ['admin'],
                'tipo_contato': 'OUTRO',
                'resumo': 'Teste',
                'produto_relacionado': 3,
            },
        }]
        normalizado = _normalizar_fixture_backup(payload)
        fields = normalizado[0]['fields']
        self.assertNotIn('produto_relacionado', fields)
        self.assertEqual(fields['produtos_relacionados'], [3])

    def test_restore_backup_25_06_com_produto_legado(self):
        path = _backup_path_2026_06_25()
        if not path.is_file():
            self.skipTest('Backup 2026-06-25 não disponível neste ambiente.')

        uploaded = SimpleUploadedFile(
            path.name,
            path.read_bytes(),
            content_type='application/zip',
        )
        restaurar_arquivo_backup(uploaded)

        self.assertGreater(AtividadeCliente.objects.ativas().count(), 0)
        com_produto = AtividadeCliente.objects.filter(
            produtos_relacionados__isnull=False,
        ).distinct().count()
        self.assertGreater(com_produto, 0)

    def test_restore_backup_antigo_sem_motivo_perda_no_json(self):
        """Backups anteriores ao campo motivo_perda devem carregar e abrir PowerUP."""
        payload = [
            {
                'model': 'accounts.usuario',
                'pk': 1,
                'fields': {
                    'password': 'pbkdf2_sha256$1000000$abc$abc=',
                    'last_login': None,
                    'is_superuser': True,
                    'username': 'admin',
                    'first_name': 'Admin',
                    'last_name': '',
                    'email': 'admin@test.com',
                    'is_staff': True,
                    'is_active': True,
                    'date_joined': '2026-01-01T10:00:00Z',
                    'papel': 'admin',
                    'taxa_comissao_padrao': '0.50',
                    'ativo': True,
                    'avatar': None,
                    'tema': 'claro',
                },
            },
            {
                'model': 'accounts.usuario',
                'pk': 2,
                'fields': {
                    'password': 'pbkdf2_sha256$1000000$abc$abc=',
                    'last_login': None,
                    'is_superuser': False,
                    'username': 'vendedor',
                    'first_name': 'Vendedor',
                    'last_name': '',
                    'email': 'v@test.com',
                    'is_staff': False,
                    'is_active': True,
                    'date_joined': '2026-01-01T10:00:00Z',
                    'papel': 'vendedor',
                    'taxa_comissao_padrao': '0.50',
                    'ativo': True,
                    'avatar': None,
                    'tema': 'claro',
                },
            },
            {
                'model': 'clientes.cliente',
                'pk': 1,
                'fields': {
                    'vendedor': 2,
                    'categoria': 'ativo',
                    'nome': 'Cliente Teste',
                    'tipo_cliente': None,
                    'modalidade_cliente': None,
                    'segmento': None,
                    'origem_lead': None,
                    'status_funil': 'NEGOCIACAO',
                    'regiao_atuacao': None,
                    'cidade': 'Curitiba',
                    'estado': 'PR',
                    'cep': '',
                    'telefone': '',
                    'responsavel': '',
                    'instagram': '',
                    'endereco': '',
                    'data_primeiro_contato': None,
                    'feedback_original': '',
                    'legacy_id': '',
                    'created_at': '2026-06-01T10:00:00Z',
                    'updated_at': '2026-06-01T10:00:00Z',
                    'created_by': 1,
                    'updated_by': 1,
                },
            },
        ]

        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('manifest.json', json.dumps(_manifest()))
            zf.writestr('data.json', json.dumps(payload))
        buf.seek(0)

        uploaded = SimpleUploadedFile('mini.karamsbackup.zip', buf.read())
        restaurar_arquivo_backup(uploaded)

        cliente = Cliente.objects.get(nome='Cliente Teste')
        self.assertEqual(cliente.motivo_perda, '')
        self.assertEqual(cliente.estado, 'PR')

        admin = Usuario.objects.get(username='admin')
        from django.test import RequestFactory
        req = RequestFactory().get('/powerup/')
        req.user = admin
        build_powerup_context(req)
