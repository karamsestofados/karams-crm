from decimal import Decimal

from datetime import date

from django.test import TestCase

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente
from comissoes.services.produtividade import (
    _filtro_propostas_orcamentos,
    calcular_realizado,
    conversao_orcamentos,
)
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao


class PropostasOrcamentosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='v_prop',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Cliente Proposta',
            categoria=CategoriaCliente.ATIVO,
        )

    def test_conta_negociacao_e_aguardando_retorno(self):
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.NEGOCIACAO,
            resumo='Orçamento enviado',
            assunto='',
            resultado=Resultado.INTERESSADO,
            proxima_acao=ProximaAcao.ENVIAR_PROPOSTA,
            data_proxima_acao=date(2026, 6, 20),
        )
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Cobrança retorno',
            assunto='',
            resultado=Resultado.AGUARDANDO_RETORNO,
            proxima_acao=ProximaAcao.LIGAR,
            data_proxima_acao=date(2026, 6, 22),
        )
        realizado = calcular_realizado(self.vendedor, 6, 2026)
        self.assertEqual(realizado['propostas'], 2)

    def test_conversao_orcamentos(self):
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.PROPOSTA,
            resumo='Orçamento 1',
            assunto='',
            resultado=Resultado.PROPOSTA_ENVIADA,
            proxima_acao=ProximaAcao.LIGAR,
            data_proxima_acao=date(2026, 6, 18),
        )
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.PROPOSTA,
            resumo='Orçamento 2',
            assunto='',
            resultado=Resultado.PROPOSTA_ENVIADA,
            proxima_acao=ProximaAcao.LIGAR,
            data_proxima_acao=date(2026, 6, 19),
        )
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Fechou pedido',
            assunto='',
            resultado=Resultado.PEDIDO_FECHADO,
            proxima_acao=ProximaAcao.SEM_ACAO,
            valor_venda=Decimal('5000'),
        )
        conv = conversao_orcamentos(
            self.vendedor,
            de=date(2026, 6, 1),
            ate=date(2026, 6, 30),
        )
        self.assertEqual(conv['enviados'], 2)
        self.assertEqual(conv['fechados'], 1)
        self.assertEqual(conv['taxa_pct'], 50.0)

    def test_filtro_q_object(self):
        q = _filtro_propostas_orcamentos()
        self.assertIsNotNone(q)
