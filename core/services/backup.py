import json
import shutil
import tempfile
import zipfile
from io import StringIO
from pathlib import Path

import django
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

BACKUP_FORMAT_VERSION = 1
BACKUP_EXTENSION = '.karamsbackup.zip'


def _manifest():
    return {
        'format_version': BACKUP_FORMAT_VERSION,
        'created_at': timezone.now().isoformat(),
        'django_version': django.get_version(),
        'app': 'karams-crm',
    }


def gerar_arquivo_backup():
    """Gera arquivo ZIP com dump completo do banco e arquivos de mídia."""
    timestamp = timezone.now().strftime('%Y-%m-%d-%H%M%S')
    filename = f'karams-backup-{timestamp}{BACKUP_EXTENSION}'

    buffer = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode='w+b')

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('manifest.json', json.dumps(_manifest(), indent=2, ensure_ascii=False))

        output = StringIO()
        call_command(
            'dumpdata',
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=output,
        )
        archive.writestr('data.json', output.getvalue())

        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for path in media_root.rglob('*'):
                if path.is_file():
                    arcname = Path('media') / path.relative_to(media_root)
                    archive.write(path, arcname.as_posix())

    buffer.seek(0)
    return buffer, filename


def _validar_backup_zip(archive):
    names = archive.namelist()
    if 'manifest.json' not in names or 'data.json' not in names:
        raise ValidationError('Arquivo inválido. Use um backup gerado pelo Karams CRM.')

    manifest = json.loads(archive.read('manifest.json'))
    if manifest.get('format_version') != BACKUP_FORMAT_VERSION:
        raise ValidationError('Versão do backup não suportada.')
    if manifest.get('app') != 'karams-crm':
        raise ValidationError('Este arquivo não é um backup do Karams CRM.')

    data_raw = archive.read('data.json')
    try:
        json.loads(data_raw)
    except json.JSONDecodeError as exc:
        raise ValidationError('Conteúdo do backup corrompido.') from exc

    return data_raw


def restaurar_arquivo_backup(uploaded_file):
    """Substitui todos os dados do sistema pelo conteúdo do backup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        zip_path = tmp / 'upload.zip'

        with open(zip_path, 'wb') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        with zipfile.ZipFile(zip_path, 'r') as archive:
            data_raw = _validar_backup_zip(archive)
            data_path = tmp / 'data.json'
            data_path.write_bytes(data_raw.encode('utf-8') if isinstance(data_raw, str) else data_raw)

            media_files = [n for n in archive.namelist() if n.startswith('media/') and not n.endswith('/')]
            if media_files:
                archive.extractall(tmp, members=media_files)

        call_command('flush', verbosity=0, interactive=False)
        call_command('loaddata', str(data_path), verbosity=0)

        extracted_media = tmp / 'media'
        media_root = Path(settings.MEDIA_ROOT)
        if extracted_media.exists():
            media_root.mkdir(parents=True, exist_ok=True)
            for item in media_root.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            for path in extracted_media.rglob('*'):
                if path.is_file():
                    rel = path.relative_to(extracted_media)
                    target = media_root / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
