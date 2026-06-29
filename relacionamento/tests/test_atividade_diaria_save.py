import json
from datetime import date, time

from django.test import TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import CategoriaCliente, Cliente, MotivoPerda
from relacionamento.models import AtividadeCliente, ProximaAcao, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao


class AtividadeDiariaSaveTests(TestCase):
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
            username='vendedor_save',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(
            vendedor=cls.vendedor,
            nome='Cliente Save Test',
            categoria=CategoriaCliente.ATIVO,
            cidade='Maringá',
            estado='PR',
        )
        cls.atividade_pendente = registrar_interacao(
            cliente=cls.cliente,
            usuario=cls.vendedor,
            tipo_contato=TipoContato.WHATSAPP,
            resumo='Follow-up anterior',
            resultado=Resultado.AGUARDANDO_RETORNO,
            proxima_acao=ProximaAcao.ENVIAR_WHATSAPP,
            data_proxima_acao=date(2026, 7, 10),
            hora_proxima_acao=time(14, 0),
        )

    def setUp(self):
        self.client.login(username='vendedor_save', password='testpass123')

    def test_interacao_sem_interesse_sem_motivo_retorna_422_com_retarget(self):
        response = self.client.post(
            reverse('atividade:interacao_nova'),
            {
                'cliente': self.cliente.pk,
                'tipo_contato': TipoContato.WHATSAPP,
                'assunto': '',
                'resumo': 'Cliente sem interesse no momento',
                'resultado': Resultado.SEM_INTERESSE,
                'humor_cliente': '',
                'produtos_relacionados': [],
                'proxima_acao': ProximaAcao.ENVIAR_WHATSAPP,
                'data_proxima_acao': '2026-07-15',
                'hora_proxima_acao': '14:15',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response['HX-Retarget'], '#modal-interacao-global-container')
        self.assertIn('motivo', response.content.decode().lower())
        self.assertEqual(AtividadeCliente.objects.filter(resumo='Cliente sem interesse no momento').count(), 0)

    def test_interacao_sem_interesse_com_motivo_salva_sem_calendario(self):
        response = self.client.post(
            reverse('atividade:interacao_nova'),
            {
                'cliente': self.cliente.pk,
                'tipo_contato': TipoContato.WHATSAPP,
                'assunto': '',
                'resumo': 'Sem interesse confirmado',
                'resultado': Resultado.SEM_INTERESSE,
                'humor_cliente': '',
                'produtos_relacionados': [],
                'motivo_perda': MotivoPerda.PRECO,
                'motivo_perda_detalhe': '',
                'proxima_acao': ProximaAcao.ENVIAR_WHATSAPP,
                'data_proxima_acao': '2026-07-15',
                'hora_proxima_acao': '14:15',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('HX-Trigger', response)
        self.assertTrue(
            AtividadeCliente.objects.filter(resumo='Sem interesse confirmado').exists()
        )

    def test_interacao_com_followup_valido_dispara_calendario(self):
        response = self.client.post(
            reverse('atividade:interacao_nova'),
            {
                'cliente': self.cliente.pk,
                'tipo_contato': TipoContato.WHATSAPP,
                'assunto': 'Linha Toscana',
                'resumo': 'Cliente solicitou proposta',
                'resultado': Resultado.PROPOSTA_ENVIADA,
                'humor_cliente': '',
                'produtos_relacionados': [],
                'proxima_acao': ProximaAcao.ENVIAR_PROPOSTA,
                'data_proxima_acao': '2026-06-17',
                'hora_proxima_acao': '09:30',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        trigger = json.loads(response['HX-Trigger'])
        self.assertIn('openGoogleCalendar', trigger)
        self.assertIn('calendar.google.com', trigger['openGoogleCalendar'])

    def test_concluir_followup_erro_retorna_422_com_retarget(self):
        response = self.client.post(
            reverse('atividade:concluir_followup', args=[self.atividade_pendente.pk]),
            {
                'resumo': '',
                'tipo_contato': TipoContato.WHATSAPP,
                'resultado': Resultado.CONTATO_REALIZADO,
                'proxima_acao': ProximaAcao.SEM_ACAO,
                'data_proxima_acao': '',
                'hora_proxima_acao': '',
            },
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response['HX-Retarget'], '#modal-concluir-container')
        self.atividade_pendente.refresh_from_db()
        self.assertFalse(self.atividade_pendente.concluida)
