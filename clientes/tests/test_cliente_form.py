from django.test import SimpleTestCase

from accounts.models import Papel, Usuario
from clientes.forms import ClienteForm


class ClienteFormHelpTextTests(SimpleTestCase):
    def test_categoria_e_status_funil_tem_ajuda(self):
        user = Usuario(username='v', papel=Papel.VENDEDOR)
        form = ClienteForm(user=user)
        self.assertIn('30 dias', form.fields['categoria'].help_text)
        self.assertIn('categoria', form.fields['status_funil'].help_text.lower())
