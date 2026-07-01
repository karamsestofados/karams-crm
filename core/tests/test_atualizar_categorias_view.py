from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente

TEST_STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


@override_settings(STORAGES=TEST_STORAGES)
class AtualizarCategoriasViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario.objects.create_user(
            username='admin',
            password='setuppass123',
            papel=Papel.ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        cls.admin = Usuario.objects.get(username='admin')
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_cat',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )

    def test_admin_move_cliente_adormecido(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Sem Contato',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )

        self.client.login(username='admin', password='setuppass123')
        response = self.client.post(reverse('accounts:atualizar_categorias'), follow=True)
        self.assertEqual(response.status_code, 200)

        cliente.refresh_from_db()
        self.assertEqual(cliente.categoria, CategoriaCliente.ADORMECIDO)

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('1 cliente(s) movido(s)' in m for m in msgs))

    def test_admin_sem_alteracoes(self):
        Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Recente',
            categoria=CategoriaCliente.ATIVO,
        )

        self.client.login(username='admin', password='setuppass123')
        response = self.client.post(reverse('accounts:atualizar_categorias'), follow=True)
        self.assertEqual(response.status_code, 200)

        msgs = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertTrue(any('Nenhum cliente precisou ser atualizado' in m for m in msgs))

    def test_vendedor_recebe_403(self):
        self.client.login(username='vendedor_cat', password='testpass123')
        response = self.client.post(reverse('accounts:atualizar_categorias'))
        self.assertEqual(response.status_code, 403)

    def test_perfil_admin_exibe_card_atualizar_categorias(self):
        self.client.login(username='admin', password='setuppass123')
        response = self.client.get(reverse('accounts:perfil'))
        self.assertContains(response, 'Atualização de categorias')
        self.assertContains(response, 'Atualizar agora')

    def test_perfil_vendedor_nao_exibe_card(self):
        self.client.login(username='vendedor_cat', password='testpass123')
        response = self.client.get(reverse('accounts:perfil'))
        self.assertNotContains(response, 'Atualização de categorias')
        self.assertNotContains(response, 'Atualizar agora')
