from django.db import migrations


def garantir_papel_admin(apps, schema_editor):
    Usuario = apps.get_model('accounts', 'Usuario')
    Usuario.objects.filter(is_superuser=True).exclude(papel='admin').update(papel='admin')
    Usuario.objects.filter(papel='admin', is_staff=False).update(is_staff=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(garantir_papel_admin, migrations.RunPython.noop),
    ]
