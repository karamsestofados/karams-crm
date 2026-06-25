import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import Produto, TipoProduto


class ProdutoBuscaAutocompleteTests(TestCase):
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
            username='vendedor_prod_busca',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.produto_blade = Produto.objects.create(
            nome='BLADE SOFA',
            tipo_produto=TipoProduto.PADRAO,
        )
        Produto.objects.create(
            nome='DAY BED FLORES',
            tipo_produto=TipoProduto.PADRAO,
        )
        Produto.objects.create(
            nome='BLADE EXCLUSIVO',
            tipo_produto=TipoProduto.EXCLUSIVO,
            ativo=False,
        )

    def test_query_curta_retorna_lista_vazia(self):
        self.client.login(username='vendedor_prod_busca', password='testpass123')
        response = self.client.get(reverse('produtos:busca'), {'q': 'B'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), [])

    def test_busca_por_nome_retorna_produtos_ativos(self):
        self.client.login(username='vendedor_prod_busca', password='testpass123')
        response = self.client.get(reverse('produtos:busca'), {'q': 'BLADE'})
        data = json.loads(response.content)
        nomes = {item['nome'] for item in data}
        self.assertIn('BLADE SOFA', nomes)
        self.assertNotIn('BLADE EXCLUSIVO', nomes)

    def test_resposta_contem_id_nome_e_tipo(self):
        self.client.login(username='vendedor_prod_busca', password='testpass123')
        response = self.client.get(reverse('produtos:busca'), {'q': 'DAY'})
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(set(data[0].keys()), {'id', 'nome', 'tipo_produto'})
