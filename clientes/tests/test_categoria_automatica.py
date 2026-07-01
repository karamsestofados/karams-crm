from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, HistoricoInteracao, TipoInteracao
from clientes.services.categoria_automatica import (
    auditar_adormecidos,
    cliente_sem_contato,
    processar_clientes_adormecidos,
    reativar_cliente_apos_interacao,
    ultima_data_contato_cliente,
)
from relacionamento.models import ProximaAcao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao


class CategoriaAutomaticaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='v_cat',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )

    def test_ativo_sem_contato_30_dias_vai_para_adormecido(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Antigo',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        total = processar_clientes_adormecidos()
        self.assertEqual(total, 1)
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ADORMECIDO)

    def test_ativo_com_historico_legado_recente_permanece_ativo(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Com histórico recente',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=90),
        )
        HistoricoInteracao.objects.create(
            cliente=cliente,
            vendedor=self.vendedor,
            data=timezone.localdate(),
            tipo=TipoInteracao.CONTATO,
            observacao='Contato legado',
        )
        processar_clientes_adormecidos()
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ATIVO)

    def test_ativo_com_historico_legado_antigo_vai_para_adormecido(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Histórico antigo',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=90),
        )
        HistoricoInteracao.objects.create(
            cliente=cliente,
            vendedor=self.vendedor,
            data=timezone.localdate() - timedelta(days=60),
            tipo=TipoInteracao.CONTATO,
            observacao='Contato antigo',
        )
        total = processar_clientes_adormecidos()
        self.assertEqual(total, 1)
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ADORMECIDO)

    def test_ultima_data_contato_usa_historico_quando_sem_atividade(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Só legado',
            categoria=CategoriaCliente.ATIVO,
        )
        data_hist = timezone.localdate() - timedelta(days=10)
        HistoricoInteracao.objects.create(
            cliente=cliente,
            vendedor=self.vendedor,
            data=data_hist,
            tipo=TipoInteracao.CONTATO,
        )
        self.assertEqual(ultima_data_contato_cliente(cliente), data_hist)
        self.assertFalse(cliente_sem_contato(cliente))

    def test_auditar_retorna_elegiveis(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Auditoria',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        rel = auditar_adormecidos()
        self.assertGreaterEqual(rel['total_elegiveis'], 1)

    def test_prospeccao_nao_muda_para_adormecido(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Lead Prospecção',
            categoria=CategoriaCliente.PROSPECCAO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        processar_clientes_adormecidos()
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.PROSPECCAO)

    def test_inativo_nao_muda(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Inativo',
            categoria=CategoriaCliente.INATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        processar_clientes_adormecidos()
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.INATIVO)

    def test_interacao_reativa_adormecido(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Adormecido',
            categoria=CategoriaCliente.ADORMECIDO,
        )
        registrar_interacao(
            cliente=cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Retomada de contato',
            resultado=Resultado.CONTATO_REALIZADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ATIVO)

    def test_interacao_reativa_prospeccao(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Lead Novo',
            categoria=CategoriaCliente.PROSPECCAO,
        )
        registrar_interacao(
            cliente=cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.LIGACAO,
            resumo='Primeiro contato',
            resultado=Resultado.CONTATO_REALIZADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ATIVO)

    def test_reativar_nao_altera_inativo(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Inativo',
            categoria=CategoriaCliente.INATIVO,
        )
        self.assertFalse(reativar_cliente_apos_interacao(cliente))
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.INATIVO)

    def test_ativo_com_interacao_recente_permanece_ativo(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Ativo',
            categoria=CategoriaCliente.ATIVO,
        )
        registrar_interacao(
            cliente=cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.EMAIL,
            resumo='Contato recente',
            resultado=Resultado.CONTATO_REALIZADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
        )
        processar_clientes_adormecidos()
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ATIVO)

    def test_management_command(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Para command',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command('atualizar_categorias_clientes', stdout=out)
        self.assertIn('1 cliente(s)', out.getvalue())
        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ADORMECIDO)
