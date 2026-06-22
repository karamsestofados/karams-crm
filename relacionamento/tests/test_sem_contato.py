from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente
from relacionamento.models import AtividadeCliente, TipoContato
from relacionamento.services.atividades import registrar_interacao
from relacionamento.services.cockpit import clientes_sem_contato


class ClientesSemContatoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='v_sem_contato',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )

    def test_nunca_contactado_usa_data_cadastro(self):
        cliente = Cliente.objects.create(
            vendedor=self.vendedor,
            nome='Cliente Novo',
            categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=cliente.pk).update(
            created_at=timezone.now() - timedelta(days=45),
        )
        cliente.refresh_from_db()
        lista = clientes_sem_contato(self.vendedor, dias=30, limit=10)
        nomes = [x['cliente'].nome for x in lista]
        self.assertIn('Cliente Novo', nomes)
        item = next(x for x in lista if x['cliente'].nome == 'Cliente Novo')
        self.assertGreaterEqual(item['dias_sem_contato'], 30)
        self.assertIsNone(item['data_ultimo_contato'])

    def test_ordenado_por_mais_dias(self):
        c1 = Cliente.objects.create(
            vendedor=self.vendedor, nome='A Antigo', categoria=CategoriaCliente.ATIVO,
        )
        c2 = Cliente.objects.create(
            vendedor=self.vendedor, nome='B Recente', categoria=CategoriaCliente.ATIVO,
        )
        Cliente.objects.filter(pk=c1.pk).update(
            created_at=timezone.now() - timedelta(days=60),
        )
        Cliente.objects.filter(pk=c2.pk).update(
            created_at=timezone.now() - timedelta(days=35),
        )
        lista = clientes_sem_contato(self.vendedor, dias=30, limit=10)
        if len(lista) >= 2:
            self.assertGreaterEqual(lista[0]['dias_sem_contato'], lista[1]['dias_sem_contato'])
