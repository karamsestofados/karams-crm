from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, StatusFunil
from comissoes.models import MetaMensal, Venda
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao
from relacionamento.services.giro_carteira import calcular_giro_carteira


class CockpitHtmxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.user = Usuario.objects.create_user(
            username='vendedor_cockpit',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )

    def test_htmx_mes_retorna_partial_sem_sidebar(self):
        self.client.login(username='vendedor_cockpit', password='testpass123')
        response = self.client.get(
            reverse('atividade:atividade_diaria') + '?ano=2026&mes=7',
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'sidebar-nav')
        self.assertContains(response, 'cockpit-calendario')


class GiroCarteiraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_giro',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.c1 = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente 1', categoria=CategoriaCliente.ATIVO)
        cls.c2 = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente 2', categoria=CategoriaCliente.ATIVO)

    def test_giro_percentual_mes_atual(self):
        hoje = timezone.localdate()
        registrar_interacao(
            cliente=self.c1,
            usuario=self.vendedor,
            tipo_contato=TipoContato.LIGACAO,
            resumo='Contato encerrado',
            resultado=Resultado.CONTATO_REALIZADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
        )
        giro = calcular_giro_carteira(self.vendedor, mes=hoje.month, ano=hoje.year)
        self.assertEqual(giro['total_clientes'], 2)
        self.assertEqual(giro['clientes_contatados'], 1)
        self.assertEqual(giro['percentual'], 50.0)
        self.assertEqual(giro['periodo_label'], f'{hoje.month:02d}/{hoje.year}')

    def test_giro_nao_conta_mes_anterior(self):
        hoje = timezone.localdate()
        atividade = registrar_interacao(
            cliente=self.c1,
            usuario=self.vendedor,
            tipo_contato=TipoContato.LIGACAO,
            resumo='Contato antigo',
            resultado=Resultado.CONTATO_REALIZADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
        )
        from relacionamento.models import AtividadeCliente
        AtividadeCliente.objects.filter(pk=atividade.pk).update(
            data_criacao=timezone.now() - timedelta(days=40),
        )
        giro = calcular_giro_carteira(self.vendedor, mes=hoje.month, ano=hoje.year)
        self.assertEqual(giro['clientes_contatados'], 0)
        self.assertEqual(giro['percentual'], 0.0)


class InteracaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_int',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Cliente Teste',
            categoria=CategoriaCliente.ATIVO,
        )

    def test_pedido_fechado_cria_venda(self):
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.VISITA,
            resumo='Venda realizada',
            resultado=Resultado.PEDIDO_FECHADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
            valor_venda=Decimal('15000.00'),
        )
        self.assertEqual(Venda.objects.filter(cliente=self.cliente).count(), 1)
        self.assertEqual(Venda.objects.get(cliente=self.cliente).valor, Decimal('15000.00'))

    def test_encerrar_atendimento_atualiza_funil(self):
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Sem interesse',
            resultado=Resultado.SEM_INTERESSE,
            proxima_acao=ProximaAcao.SEM_ACAO,
            motivo_perda='PRECO',
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.status_funil, StatusFunil.CLIENTE_PERDIDO)
        self.assertIsNotNone(self.cliente.data_primeiro_contato)
        atividade = AtividadeCliente.objects.get(cliente=self.cliente)
        self.assertTrue(atividade.concluida)
