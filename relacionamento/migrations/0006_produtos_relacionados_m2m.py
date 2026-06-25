from django.db import migrations, models


def copiar_produto_fk_para_m2m(apps, schema_editor):
    AtividadeCliente = apps.get_model('relacionamento', 'AtividadeCliente')
    for atividade in AtividadeCliente.objects.exclude(produto_relacionado_id__isnull=True):
        atividade.produtos_relacionados.add(atividade.produto_relacionado_id)


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
        ('relacionamento', '0005_atividadeclienteedicao'),
    ]

    operations = [
        migrations.AddField(
            model_name='atividadecliente',
            name='produtos_relacionados',
            field=models.ManyToManyField(
                blank=True,
                related_name='atividades_relacionadas',
                to='clientes.produto',
                verbose_name='produtos relacionados',
            ),
        ),
        migrations.RunPython(copiar_produto_fk_para_m2m, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='atividadecliente',
            name='produto_relacionado',
        ),
    ]
