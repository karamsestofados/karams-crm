from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from comissoes.models import MetaMensal


class MetaMensalTests(TestCase):
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
            username='admin_meta',
            password='testpass123',
            papel=Papel.ADMIN,
            is_staff=True,
        )
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_meta',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.meta_equipe = MetaMensal.objects.create(
            vendedor=None,
            mes=6,
            ano=2026,
            meta_contatos=100,
        )

    def test_listagem_meta_equipe_sem_erro(self):
        self.client.login(username='admin_meta', password='testpass123')
        response = self.client.get(reverse('comissoes:metas_lista'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Equipe')

    def test_filtro_mes(self):
        self.client.login(username='admin_meta', password='testpass123')
        response = self.client.get(reverse('comissoes:metas_lista') + '?mes=6')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Equipe')

    def test_filtro_equipe(self):
        self.client.login(username='admin_meta', password='testpass123')
        response = self.client.get(reverse('comissoes:metas_lista') + '?vendedor=equipe')
        self.assertEqual(response.status_code, 200)

    def test_criar_meta_duplicada_rejeitada(self):
        self.client.login(username='admin_meta', password='testpass123')
        response = self.client.post(reverse('comissoes:metas_nova'), {
            'vendedor': '',
            'mes': 6,
            'ano': 2026,
            'meta_contatos': 50,
            'meta_clientes_novos': 0,
            'meta_propostas': 0,
            'meta_visitas': 0,
            'meta_vendas': '80000',
            'observacoes': '',
            'ativo': True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Já existe uma meta')
