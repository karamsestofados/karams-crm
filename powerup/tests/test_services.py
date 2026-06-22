from datetime import date

from django.test import TestCase

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, MotivoPerda, StatusFunil
from comissoes.services.produtividade import _aplicar_filtros_cliente
from powerup.services.funil import funil_comercial
from powerup.services.motivo_perda import relatorio_motivo_perda
from powerup.services.saude_carteira import saude_carteira
from relacionamento.services.clientes_quentes import listar_clientes_quentes


class PowerUPServicesTest(TestCase):
    def setUp(self):
        self.vendedor = Usuario.objects.create_user(
            username='v1', password='x', papel=Papel.VENDEDOR, first_name='Fabiana',
        )
        self.admin = Usuario.objects.create_user(
            username='admin', password='x', papel=Papel.ADMIN, is_staff=True,
        )
        self.cliente_pr = Cliente.objects.create(
            vendedor=self.vendedor, nome='Cliente PR', categoria=CategoriaCliente.ATIVO,
            estado='PR', status_funil=StatusFunil.NEGOCIACAO,
        )
        Cliente.objects.create(
            vendedor=self.vendedor, nome='Cliente SP', categoria=CategoriaCliente.ATIVO,
            estado='SP', status_funil=StatusFunil.LEAD_NOVO,
        )

    def test_filtro_uf_produtividade(self):
        qs = Cliente.objects.all()
        filtrado = _aplicar_filtros_cliente(qs, {'estado': 'PR'})
        self.assertEqual(filtrado.count(), 1)
        self.assertEqual(filtrado.first().estado, 'PR')

    def test_funil_comercial(self):
        funil = funil_comercial(self.vendedor)
        self.assertEqual(len(funil), 4)
        self.assertGreaterEqual(funil[0]['total'], 1)

    def test_motivo_perda_relatorio(self):
        self.cliente_pr.status_funil = StatusFunil.CLIENTE_PERDIDO
        self.cliente_pr.motivo_perda = MotivoPerda.PRECO
        self.cliente_pr.save()
        rel = relatorio_motivo_perda(self.vendedor)
        self.assertEqual(rel['total'], 1)
        self.assertEqual(rel['itens'][0]['motivo'], MotivoPerda.PRECO)

    def test_saude_carteira_vendedor(self):
        saude = saude_carteira(self.vendedor)
        self.assertEqual(saude['propria']['total'], 2)
        self.assertIn('pct_saudavel', saude['propria'])

    def test_clientes_quentes_escopo(self):
        quentes = listar_clientes_quentes(self.vendedor, limit=6)
        self.assertTrue(all(item['cliente'].vendedor_id == self.vendedor.pk for item in quentes))

    def test_clientes_quentes_admin_ve_todos(self):
        quentes = listar_clientes_quentes(self.admin, limit=6)
        nomes = {item['cliente'].nome for item in quentes}
        self.assertTrue('Cliente PR' in nomes or 'Cliente SP' in nomes)
