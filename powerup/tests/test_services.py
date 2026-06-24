from datetime import date

from django.test import TestCase

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, MotivoPerda, StatusFunil
from comissoes.services.produtividade import _aplicar_filtros_cliente
from powerup.services.funil import funil_comercial
from powerup.services.motivo_perda import relatorio_motivo_perda
from powerup.services.saude_carteira import calcular_indice_saude, classificar_indice_saude, saude_carteira
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
        self.assertIn('indice', saude['propria'])
        self.assertIn('status_label', saude['propria'])

    def test_indice_saude_formula(self):
        indice = calcular_indice_saude(62.9, 12.9, 12.9)
        self.assertEqual(indice, 28)
        status = classificar_indice_saude(indice)
        self.assertEqual(status['label'], 'Risco')
        self.assertEqual(status['classe'], 'risco')

    def test_classificar_indice_saude_faixas(self):
        self.assertEqual(classificar_indice_saude(85)['label'], 'Excelente')
        self.assertEqual(classificar_indice_saude(70)['label'], 'Saudável')
        self.assertEqual(classificar_indice_saude(50)['label'], 'Atenção')
        self.assertEqual(classificar_indice_saude(25)['label'], 'Risco')
        self.assertEqual(classificar_indice_saude(10)['label'], 'Crítica')

    def test_clientes_quentes_escopo(self):
        quentes = listar_clientes_quentes(self.vendedor, limit=6)
        self.assertTrue(all(item['cliente'].vendedor_id == self.vendedor.pk for item in quentes))

    def test_clientes_quentes_admin_ve_todos(self):
        quentes = listar_clientes_quentes(self.admin, limit=6)
        nomes = {item['cliente'].nome for item in quentes}
        self.assertTrue('Cliente PR' in nomes or 'Cliente SP' in nomes)
