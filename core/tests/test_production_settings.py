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
