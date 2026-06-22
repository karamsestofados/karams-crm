from decimal import Decimal

from django.test import SimpleTestCase

from core.templatetags.karams_formats import brl, brl_int, num_br


class KaramsFormatsTests(SimpleTestCase):
    def test_brl(self):
        self.assertEqual(brl(150000), 'R$ 150.000,00')
        self.assertEqual(brl(Decimal('23892.5')), 'R$ 23.892,50')

    def test_brl_int(self):
        self.assertEqual(brl_int(235000), 'R$ 235.000')

    def test_num_br(self):
        self.assertEqual(num_br(150000), '150.000')
