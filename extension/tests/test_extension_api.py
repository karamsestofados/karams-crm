from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, Produto, StatusFunil, TipoInteracao
from comissoes.models import Venda
from extension.models import ExtensionApiToken
from extension.services.contexto_whatsapp import (
    alertas_cliente,
    buscar_cliente_por_telefone,
    metricas_compra_cliente,
    montar_contexto_extension,
)
from extension.services.telefone import telefones_equivalentes


class TelefoneUtilsTests(TestCase):
    def test_equivalentes_com_ddi_e_formatacao(self):
        self.assertTrue(telefones_equivalentes('5544999887766', '(44) 99988-7766'))
        self.assertTrue(telefones_equivalentes('44999887766', '5544999887766'))
        self.assertFalse(telefones_equivalentes('44999887766', '44999887755'))

    def test_equivalentes_nono_digito_celular_br(self):
        # WhatsApp exibe 9971-2271 (10 dígitos locais); CRM tem 99971-2271 (11)
        self.assertTrue(telefones_equivalentes('+55 71 9971-2271', '(71) 99971-2271'))
        self.assertTrue(telefones_equivalentes('557199712271', '71999712271'))
        self.assertFalse(telefones_equivalentes('7199712271', '7199712272'))


class ExtensionApiTests(TestCase):
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
            username='vendedor_ext',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.outro = Usuario.objects.create_user(
            username='outro_ext',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            nome='João Silva',
            vendedor=cls.vendedor,
            telefone='(44) 99988-7766',
            cidade='Maringá',
            estado='PR',
            categoria=CategoriaCliente.ATIVO,
            status_funil=StatusFunil.CLIENTE_ATIVO,
        )
        cls.cliente_outro = Cliente.objects.create(
            nome='Cliente Outro',
            vendedor=cls.outro,
            telefone='(11) 98888-7777',
        )
        _, cls.token_raw = ExtensionApiToken.gerar_para_usuario(cls.vendedor)

    def _auth(self, token=None):
        return {'HTTP_AUTHORIZATION': f'Bearer {token or self.token_raw}'}

    def test_me_autenticado(self):
        resp = self.client.get(reverse('extension:me'), **self._auth())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['username'], 'vendedor_ext')

    def test_me_sem_token(self):
        resp = self.client.get(reverse('extension:me'))
        self.assertEqual(resp.status_code, 401)

    def test_contexto_cliente_encontrado(self):
        Venda.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            data=timezone.localdate(),
            valor=Decimal('8450.00'),
        )
        resp = self.client.get(
            reverse('extension:contexto'),
            {'telefone': '5544999887766'},
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['encontrado'])
        self.assertEqual(data['cliente']['nome'], 'João Silva')
        self.assertEqual(data['metricas']['ultima_compra_valor'], '8450.00')

    def test_contexto_cliente_nao_encontrado(self):
        resp = self.client.get(
            reverse('extension:contexto'),
            {'telefone': '5511999999999'},
            **self._auth(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['encontrado'])

    def test_busca_cliente_nono_digito(self):
        cliente_ba = Cliente.objects.create(
            nome='MF Vieira',
            vendedor=self.vendedor,
            telefone='(71) 99971-2271',
        )
        found = buscar_cliente_por_telefone(self.vendedor, '557199712271')
        self.assertEqual(found, cliente_ba)

    def test_vendedor_nao_ve_cliente_de_outro(self):
        found = buscar_cliente_por_telefone(self.vendedor, '11988887777')
        self.assertIsNone(found)

    def test_metricas_vazio(self):
        metricas = metricas_compra_cliente(self.cliente)
        self.assertIsNone(metricas['ultima_compra_valor'])

    def test_alertas_sem_compra(self):
        Venda.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            data=timezone.localdate() - timedelta(days=50),
            valor=Decimal('1000.00'),
        )
        alertas = alertas_cliente(self.cliente, self.vendedor)
        codigos = {a['codigo'] for a in alertas}
        self.assertIn('SEM_COMPRA_45D', codigos)

    def test_montar_contexto_request(self):
        req = self.client.get('/').wsgi_request
        payload = montar_contexto_extension(req, self.vendedor, '5544999887766')
        self.assertTrue(payload['encontrado'])
        self.assertIn('url_crm', payload['cliente'])

    def test_token_revogado(self):
        ExtensionApiToken.objects.filter(usuario=self.vendedor).update(ativo=False)
        resp = self.client.get(reverse('extension:me'), **self._auth())
        self.assertEqual(resp.status_code, 401)

    def test_ultimo_produto_comprado_com_m2m(self):
        produto = Produto.objects.create(nome='Sofá Dubai Retrátil')
        venda = Venda.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            data=timezone.localdate(),
            valor=Decimal('6198.35'),
            produtos_texto='Pedido fechado',
        )
        venda.produtos.add(produto)
        resp = self.client.get(
            reverse('extension:contexto'),
            {'telefone': '5544999887766'},
            **self._auth(),
        )
        data = resp.json()
        self.assertEqual(data['metricas']['ultimo_produto_comprado'], 'Sofá Dubai Retrátil')
        self.assertEqual(data['metricas']['ultima_compra_referencia'], f'Pedido #{venda.pk}')
        self.assertEqual(data['metricas']['produto_mais_comprado'], 'Sofá Dubai Retrátil')

    def test_ultimo_produto_ignora_texto_generico(self):
        Venda.objects.create(
            cliente=self.cliente,
            vendedor=self.vendedor,
            data=timezone.localdate(),
            valor=Decimal('1000.00'),
            produtos_texto='Pedido fechado',
        )
        metricas = metricas_compra_cliente(self.cliente)
        self.assertIsNone(metricas['ultimo_produto_comprado'])

    def test_consultor_nome_no_contexto(self):
        self.vendedor.first_name = 'André'
        self.vendedor.last_name = 'Felipe'
        self.vendedor.save(update_fields=['first_name', 'last_name'])
        resp = self.client.get(
            reverse('extension:contexto'),
            {'telefone': '5544999887766'},
            **self._auth(),
        )
        data = resp.json()
        self.assertEqual(data['cliente']['consultor_nome'], 'André Felipe')
