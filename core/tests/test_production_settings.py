from django.test import SimpleTestCase

from karams_crm.settings.production import (
    _build_csrf_trusted_origins,
    _normalize_allowed_hosts,
)


class ProductionSettingsTest(SimpleTestCase):
    def test_normalize_wildcard_hosts(self):
        hosts = _normalize_allowed_hosts(['*.railway.app', 'crm-karams.up.railway.app'])
        self.assertIn('.railway.app', hosts)
        self.assertIn('crm-karams.up.railway.app', hosts)

    def test_csrf_rejects_wildcard_origins(self):
        origins = _build_csrf_trusted_origins(
            ['.railway.app', 'crm-karams.up.railway.app'],
            'crm-karams.up.railway.app',
        )
        self.assertIn('https://crm-karams.up.railway.app', origins)
        self.assertTrue(all('*' not in o for o in origins))

    def test_csrf_includes_explicit_allowed_hosts(self):
        origins = _build_csrf_trusted_origins(
            ['crm-karams.up.railway.app'],
            '',
        )
        self.assertEqual(origins, ['https://crm-karams.up.railway.app'])


class ConversaoPowerUPTest(SimpleTestCase):
    def test_conversao_por_vendedor_calls_realizado_with_mes_ano(self):
        from datetime import date
        from unittest.mock import patch

        from accounts.models import Papel, Usuario
        from powerup.services.conversao import conversao_por_vendedor

        v = Usuario(username='v', papel=Papel.VENDEDOR)
        v.pk = 1
        de = date(2026, 6, 1)
        ate = date(2026, 6, 23)

        with patch('powerup.services.conversao.Usuario.objects') as mock_u, \
             patch('powerup.services.conversao.calcular_realizado') as mock_cr, \
             patch('powerup.services.conversao.Cliente.objects') as mock_c, \
             patch('powerup.services.conversao.AtividadeCliente.objects') as mock_a, \
             patch('powerup.services.conversao.Venda.objects') as mock_v:
            mock_u.filter.return_value.order_by.return_value = [v]
            mock_c.filter.return_value.filter.return_value.count.return_value = 0
            mock_a.ativas.return_value.filter.return_value.count.return_value = 0
            mock_v.filter.return_value.count.return_value = 0
            mock_cr.return_value = {'propostas': 0}

            admin = Usuario(username='admin', papel=Papel.ADMIN)
            admin.pk = 2
            conversao_por_vendedor(de, ate, admin)

            mock_cr.assert_called_once()
            args, kwargs = mock_cr.call_args
            self.assertEqual(args[1], 6)
            self.assertEqual(args[2], 2026)
            self.assertEqual(kwargs['de'], de)
            self.assertEqual(kwargs['ate'], ate)
