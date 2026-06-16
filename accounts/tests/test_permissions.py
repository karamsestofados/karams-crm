from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from comissoes.models import MetaMensal


class PermissionSmokeTests(TestCase):
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
            username='admin_test',
            password='testpass123',
            papel=Papel.ADMIN,
            is_staff=True,
        )
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_test',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.outro_vendedor = Usuario.objects.create_user(
            username='vendedor2',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente_outro = Cliente.objects.create(
            vendedor=cls.outro_vendedor,
            nome='Cliente Outro',
        )

    def test_admin_acessa_usuarios(self):
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('accounts:usuarios_lista'))
        self.assertEqual(response.status_code, 200)

    def test_vendedor_bloqueado_usuarios(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('accounts:usuarios_lista'))
        self.assertEqual(response.status_code, 403)

    def test_admin_acessa_metas(self):
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('comissoes:metas_lista'))
        self.assertEqual(response.status_code, 200)

    def test_vendedor_bloqueado_metas(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('comissoes:metas_lista'))
        self.assertEqual(response.status_code, 403)

    def test_vendedor_bloqueado_admin_django(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 403)

    def test_vendedor_nao_acessa_cliente_outro(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(
            reverse('clientes:lista') + f'?id={self.cliente_outro.pk}',
        )
        self.assertEqual(response.status_code, 403)

    def test_vendedor_acessa_produtividade(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('relatorios:produtividade'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_admin(self):
        self.client.login(username='admin_test', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_vendedor(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
