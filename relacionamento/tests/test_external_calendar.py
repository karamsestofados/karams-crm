from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente
from relacionamento.forms import AtividadeClienteForm, ConcluirFollowupForm
from relacionamento.models import ProximaAcao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao
from relacionamento.services.external_calendar.dispatcher import resolve_calendar_url
from relacionamento.services.external_calendar.google import build_google_calendar_url
from relacionamento.services.external_calendar.event import CalendarEvent
from relacionamento.services.external_calendar.policy import (
    MSG_FOLLOWUP_OBRIGATORIO,
    should_open_calendar,
)


class GoogleCalendarUrlTests(TestCase):
    def test_build_url_with_accent_encoding(self):
        event = CalendarEvent(
            title='Enviar proposta - Cliente São Paulo',
            description='Resumo com acentuação: proposta revisada.',
            start_date=date(2026, 6, 17),
            start_time=time(9, 30),
            location='Maringá/PR',
        )
        url = build_google_calendar_url(event)
        self.assertIn('action=TEMPLATE', url)
        self.assertIn('calendar.google.com', url)
        self.assertIn('20260617T093000', url)
        self.assertIn('20260617T103000', url)
        self.assertIn('%C3%A3', url)

    def test_default_hora_nove_em_ponto(self):
        cliente = Cliente(nome='Cliente Teste', vendedor_id=1)
        usuario = Usuario(username='v', first_name='Vendedor')
        cleaned = {
            'proxima_acao': ProximaAcao.ENVIAR_PROPOSTA,
            'data_proxima_acao': date(2026, 6, 17),
            'hora_proxima_acao': None,
            'resultado': Resultado.CONTATO_REALIZADO,
            'tipo_contato': TipoContato.WHATSAPP,
            'resumo': 'Teste',
            'assunto': '',
            'produto_relacionado': None,
        }
        url = resolve_calendar_url(cliente, usuario, cleaned)
        self.assertIn('T090000', url)

    def test_sem_acao_nao_abre(self):
        self.assertFalse(should_open_calendar(
            ProximaAcao.SEM_ACAO, date(2026, 6, 17), Resultado.CONTATO_REALIZADO,
        ))

    def test_pedido_fechado_bloqueia(self):
        self.assertFalse(should_open_calendar(
            ProximaAcao.ENVIAR_PROPOSTA, date(2026, 6, 17), Resultado.PEDIDO_FECHADO,
        ))


class FollowupValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_cal',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Cliente Teste',
            categoria=CategoriaCliente.ATIVO,
        )

    def test_aguardando_retorno_sem_data_rejeitado(self):
        form = AtividadeClienteForm({
            'tipo_contato': TipoContato.WHATSAPP,
            'assunto': '',
            'resumo': 'Negociação em andamento',
            'resultado': Resultado.AGUARDANDO_RETORNO,
            'humor_cliente': '',
            'produto_relacionado': '',
            'proxima_acao': ProximaAcao.SEM_ACAO,
            'data_proxima_acao': '',
            'hora_proxima_acao': '',
        }, cliente=self.cliente)
        self.assertFalse(form.is_valid())
        self.assertIn(MSG_FOLLOWUP_OBRIGATORIO, form.non_field_errors())

    def test_save_independente_de_popup(self):
        cleaned = {
            'tipo_contato': TipoContato.WHATSAPP,
            'assunto': 'Linha Toscana',
            'resumo': 'Proposta enviada',
            'resultado': Resultado.PROPOSTA_ENVIADA,
            'proxima_acao': ProximaAcao.ENVIAR_PROPOSTA,
            'data_proxima_acao': date(2026, 6, 17),
            'hora_proxima_acao': time(9, 30),
            'produto_relacionado': None,
        }
        atividade = registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            valor_venda=None,
            **cleaned,
        )
        self.assertIsNotNone(atividade.pk)
        url = resolve_calendar_url(self.cliente, self.vendedor, cleaned)
        self.assertIsNotNone(url)


class CalendarHtmxTests(TestCase):
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
            username='vendedor_htmx',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Cliente HTMX',
            categoria=CategoriaCliente.ATIVO,
            cidade='Maringá',
            estado='PR',
        )

    def test_interacao_post_dispara_hx_trigger(self):
        self.client.login(username='vendedor_htmx', password='testpass123')
        response = self.client.post(
            '/atividade-diaria/interacao/nova/',
            {
                'cliente': self.cliente.pk,
                'tipo_contato': TipoContato.WHATSAPP,
                'assunto': 'Linha Toscana',
                'resumo': 'Cliente solicitou proposta',
                'resultado': Resultado.PROPOSTA_ENVIADA,
                'humor_cliente': '',
                'produto_relacionado': '',
                'proxima_acao': ProximaAcao.ENVIAR_PROPOSTA,
                'data_proxima_acao': '2026-06-17',
                'hora_proxima_acao': '09:30',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        trigger = response.headers.get('HX-Trigger', '')
        self.assertIn('openExternalCalendar', trigger)
        self.assertIn('calendar.google.com', trigger)
