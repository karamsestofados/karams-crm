from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from comissoes.models import Venda
from relacionamento.models import AtividadeCliente, AtividadeClienteEdicao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao
from relacionamento.services.dashboard import kpis_relacionamento
from relacionamento.services.editar_atividade import editar_atividade


class EditarAtividadeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.vendedor_a = Usuario.objects.create_user(
            username='fabiana',
            password='testpass123',
            papel=Papel.VENDEDOR,
            first_name='Fabiana',
        )
        cls.vendedor_b = Usuario.objects.create_user(
            username='andre',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(vendedor=cls.vendedor_a, nome='Cliente Teste')

    def _criar_venda_atividade(self, usuario, valor):
        return registrar_interacao(
            cliente=self.cliente,
            usuario=usuario,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Venda registrada',
            resultado=Resultado.PEDIDO_FECHADO,
            valor_venda=Decimal(str(valor)),
        )

    def test_vendedor_edita_propria_atividade(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '14233.90')
        edicao = editar_atividade(
            atividade,
            self.vendedor_a,
            {'valor_venda': Decimal('14183.90')},
        )
        self.assertIsNotNone(edicao)
        atividade.refresh_from_db()
        self.assertEqual(atividade.valor_venda, Decimal('14183.90'))
        self.assertEqual(AtividadeClienteEdicao.objects.count(), 1)

    def test_vendedor_bloqueado_edita_atividade_de_outro(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '1000.00')
        with self.assertRaises(PermissionDenied):
            editar_atividade(atividade, self.vendedor_b, {'resumo': 'Tentativa'})

    def test_admin_edita_qualquer_atividade(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '5000.00')
        admin = Usuario.objects.get(username='admin')
        editar_atividade(atividade, admin, {'resumo': 'Corrigido pelo admin'})
        atividade.refresh_from_db()
        self.assertEqual(atividade.resumo, 'Corrigido pelo admin')

    def test_edicao_valor_atualiza_venda(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '14233.90')
        venda = Venda.objects.filter(atividade_origem=atividade).first()
        self.assertIsNotNone(venda)
        editar_atividade(atividade, self.vendedor_a, {'valor_venda': Decimal('14000.00')})
        venda.refresh_from_db()
        self.assertEqual(venda.valor, Decimal('14000.00'))

    def test_edicao_nao_incrementa_contatos_hoje(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '1000.00')
        antes = kpis_relacionamento(self.vendedor_a)['contatos_hoje']
        editar_atividade(atividade, self.vendedor_a, {'resumo': 'Ajuste de texto'})
        depois = kpis_relacionamento(self.vendedor_a)['contatos_hoje']
        self.assertEqual(antes, depois)

    def test_post_editar_via_view(self):
        atividade = self._criar_venda_atividade(self.vendedor_a, '2000.00')
        self.client.login(username='fabiana', password='testpass123')
        response = self.client.post(
            reverse('clientes:atividade_editar', args=[self.cliente.pk, atividade.pk]),
            {
                'tipo_contato': atividade.tipo_contato,
                'assunto': atividade.assunto,
                'resumo': 'Resumo atualizado',
                'resultado': atividade.resultado,
                'humor_cliente': '',
                'valor_venda': '1950.00',
                'produto_relacionado': '',
                'proxima_acao': 'SEM_ACAO',
                'data_proxima_acao': '',
                'hora_proxima_acao': '',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        atividade.refresh_from_db()
        self.assertEqual(atividade.resumo, 'Resumo atualizado')
