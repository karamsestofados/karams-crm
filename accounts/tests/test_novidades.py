from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from core.novidades import SESSION_KEY


class NovidadesPopupTests(TestCase):
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
            username='vendedor_test',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )

    def test_login_post_marca_sessao_novidades(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'vendedor_test', 'password': 'testpass123'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get(SESSION_KEY))

    def test_dashboard_com_flag_exibe_modal(self):
        session = self.client.session
        session[SESSION_KEY] = True
        session.save()
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('modal-novidades', content)
        self.assertIn('Novidades da', content)
        self.assertIn('drive.google.com/drive/folders/18NQNOaPDePBdQf4iB488sC-CNo8LKUY6', content)
        self.assertIn('wa.me/5544988133500', content)
        self.assertIn('Integração WhatsApp Web', content)

    def test_dashboard_sem_flag_nao_exibe_modal(self):
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('modal-novidades', response.content.decode())

    def test_dispensar_remove_flag_sessao(self):
        session = self.client.session
        session[SESSION_KEY] = True
        session.save()
        self.client.login(username='vendedor_test', password='testpass123')
        response = self.client.post(reverse('accounts:novidades_dispensar'))
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.client.session.get(SESSION_KEY))

    def test_dispensar_requer_autenticacao(self):
        response = self.client.post(reverse('accounts:novidades_dispensar'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
