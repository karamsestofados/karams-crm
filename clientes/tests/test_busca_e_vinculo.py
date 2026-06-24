import json

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, ClienteProduto, Produto, TipoProduto
from clientes.services.produtos import obter_alerta_vinculo, vincular_produto


class ClienteBuscaAutocompleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.admin = Usuario.objects.create_user(
            username='admin_busca',
            password='testpass123',
            papel=Papel.ADMIN,
            is_staff=True,
        )
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_busca',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.outro_vendedor = Usuario.objects.create_user(
            username='vendedor_outro',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente_vendedor = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Loja Alpha Comercial',
        )
        cls.cliente_outro = Cliente.objects.create(
            vendedor=cls.outro_vendedor,
            nome='Loja Beta Distribuidora',
        )
        cls.cliente_inativo = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Loja Inativa Alpha',
            categoria=CategoriaCliente.INATIVO,
        )

    def test_query_curta_retorna_lista_vazia(self):
        self.client.login(username='admin_busca', password='testpass123')
        response = self.client.get(reverse('clientes:busca'), {'q': 'L'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

    def test_admin_ve_clientes_de_todos_vendedores(self):
        self.client.login(username='admin_busca', password='testpass123')
        response = self.client.get(reverse('clientes:busca'), {'q': 'Loja'})
        data = json.loads(response.content)
        nomes = {item['nome'] for item in data}
        self.assertIn('Loja Alpha Comercial', nomes)
        self.assertIn('Loja Beta Distribuidora', nomes)
        self.assertNotIn('Loja Inativa Alpha', nomes)

    def test_vendedor_ve_apenas_propria_carteira(self):
        self.client.login(username='vendedor_busca', password='testpass123')
        response = self.client.get(reverse('clientes:busca'), {'q': 'Loja'})
        data = json.loads(response.content)
        nomes = {item['nome'] for item in data}
        self.assertIn('Loja Alpha Comercial', nomes)
        self.assertNotIn('Loja Beta Distribuidora', nomes)

    def test_resposta_contem_apenas_id_e_nome(self):
        self.client.login(username='admin_busca', password='testpass123')
        response = self.client.get(reverse('clientes:busca'), {'q': 'Alpha'})
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(set(data[0].keys()), {'id', 'nome'})


class ObterAlertaVinculoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_alerta',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente_a = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente A')
        cls.cliente_b = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente B')
        cls.produto_padrao = Produto.objects.create(nome='SOFA PADRAO', tipo_produto=TipoProduto.PADRAO)
        cls.produto_exclusivo = Produto.objects.create(nome='SOFA EXCLUSIVO', tipo_produto=TipoProduto.EXCLUSIVO)
        cls.produto_unico = Produto.objects.create(nome='SOFA UNICO', tipo_produto=TipoProduto.UNICO)

    def test_padrao_sem_vinculos_retorna_none(self):
        self.assertIsNone(obter_alerta_vinculo(self.produto_padrao, self.cliente_b))

    def test_exclusivo_com_vinculo_retorna_alerta_medio(self):
        ClienteProduto.objects.create(cliente=self.cliente_a, produto=self.produto_exclusivo)
        alerta = obter_alerta_vinculo(self.produto_exclusivo, self.cliente_b)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta['nivel'], 'medio')
        self.assertFalse(alerta['bloquear'])
        self.assertEqual(alerta['clientes'], ['Cliente A'])

    def test_unico_com_vinculo_retorna_alerta_alto(self):
        ClienteProduto.objects.create(cliente=self.cliente_a, produto=self.produto_unico)
        alerta = obter_alerta_vinculo(self.produto_unico, self.cliente_b)
        self.assertIsNotNone(alerta)
        self.assertEqual(alerta['nivel'], 'alto')
        self.assertTrue(alerta['bloquear'])
        self.assertEqual(alerta['clientes'], ['Cliente A'])

    def test_sem_outros_vinculos_retorna_none(self):
        self.assertIsNone(obter_alerta_vinculo(self.produto_exclusivo, self.cliente_a))


class VincularProdutoUnicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_vinculo',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente_a = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente Origem')
        cls.cliente_b = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente Destino')
        cls.produto_unico = Produto.objects.create(nome='AKIRA', tipo_produto=TipoProduto.UNICO)

    def setUp(self):
        ClienteProduto.objects.filter(produto=self.produto_unico).delete()

    def test_vincular_unico_duplicado_levanta_validation_error(self):
        vincular_produto(self.cliente_a, self.produto_unico)
        with self.assertRaises(ValidationError):
            vincular_produto(self.cliente_b, self.produto_unico)

    def test_post_vincular_unico_ocupado_retorna_erro(self):
        vincular_produto(self.cliente_a, self.produto_unico)
        self.client.login(username='vendedor_vinculo', password='testpass123')
        response = self.client.post(
            reverse('clientes:produto_vincular', args=[self.cliente_b.pk]),
            {'produto': self.produto_unico.pk, 'observacoes': ''},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            ClienteProduto.objects.filter(cliente=self.cliente_b, produto=self.produto_unico).exists(),
        )

    def test_aviso_json_unico_ocupado(self):
        vincular_produto(self.cliente_a, self.produto_unico)
        self.client.login(username='vendedor_vinculo', password='testpass123')
        response = self.client.get(
            reverse('clientes:produto_vinculo_aviso', args=[self.cliente_b.pk]),
            {'produto': self.produto_unico.pk, 'format': 'json'},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['alerta']['bloquear'])
        self.assertEqual(data['alerta']['nivel'], 'alto')
