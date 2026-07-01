from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TransactionTestCase

from clientes.models import CategoriaCliente, Cliente
from clientes.services.categoria_automatica import auditar_adormecidos, processar_clientes_adormecidos
from core.services.backup import restaurar_arquivo_backup


def _backup_path_2026_07_01():
    return Path(
        r'c:\Users\T.I E MANUTENÇÃO\Downloads\karams-backup-2026-07-01-142445.karamsbackup.zip',
    )


class AdormecidoBackupIntegrationTest(TransactionTestCase):
    def test_backup_07_01_auditoria_e_processamento(self):
        path = _backup_path_2026_07_01()
        if not path.is_file():
            self.skipTest('Backup 2026-07-01 não disponível neste ambiente.')

        uploaded = SimpleUploadedFile(
            path.name,
            path.read_bytes(),
            content_type='application/zip',
        )
        restaurar_arquivo_backup(uploaded)

        rel = auditar_adormecidos()
        self.assertGreater(Cliente.objects.count(), 0)
        self.assertIn(CategoriaCliente.ATIVO, rel['por_categoria'])

        if rel['total_elegiveis'] > 0:
            movidos = processar_clientes_adormecidos()
            self.assertEqual(movidos, rel['total_elegiveis'])
            rel_depois = auditar_adormecidos()
            self.assertEqual(rel_depois['total_elegiveis'], 0)
        else:
            self.skipTest(
                'Backup sem Ativos elegíveis no momento do teste '
                f'(ativos={rel["ativos_total"]}, categorias={rel["por_categoria"]}).',
            )
