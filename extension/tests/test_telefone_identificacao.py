"""
Matriz de identificação de telefone — base da extensão WhatsApp.

Cenários:
- DDI (+55) e sem DDI
- Formato WhatsApp (nono dígito) vs CRM
- Celular vs fixo comercial
- Múltiplos telefones no campo CRM
- Duplicatas no CRM
- Formatações diversas
- Número inexistente (não cadastrado)

Nota: "salvo vs não salvo no WhatsApp" é detecção no content.js (painel/DOM/Store);
a API só compara o número recebido com o CRM.
"""
import shutil
import subprocess
from pathlib import Path
from unittest import skipIf

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import Papel, Usuario
from clientes.models import Cliente
from extension.models import ExtensionApiToken
from extension.services.contexto_whatsapp import buscar_cliente_por_telefone
from extension.services.telefone import (
    extrair_partes_telefone_crm,
    sufixos8_comparacao,
    telefones_equivalentes,
    variantes_chave_telefone,
    variantes_telefones_crm,
)


class TelefoneIdentificacaoMatrizTests(TestCase):
    """Equivalência entre formatos de entrada (WhatsApp, CRM, API)."""

    def test_com_ddi_mais_55(self):
        casos = [
            ('+55 44 99988-7766', '(44) 99988-7766'),
            ('5544999887766', '(44) 99988-7766'),
            ('+55 (44) 99988-7766', '44999887766'),
        ]
        for a, b in casos:
            with self.subTest(a=a, b=b):
                self.assertTrue(telefones_equivalentes(a, b), f'{a!r} deveria equivaler a {b!r}')

    def test_sem_ddi(self):
        casos = [
            ('44999887766', '(44) 99988-7766'),
            ('44999887766', '5544999887766'),
            ('7199712271', '557199712271'),
        ]
        for a, b in casos:
            with self.subTest(a=a, b=b):
                self.assertTrue(telefones_equivalentes(a, b))

    def test_formato_whatsapp_nono_digito(self):
        """WhatsApp exibe 9971-2271 (10 locais); CRM guarda 99971-2271 (11)."""
        whatsapp = '+55 71 9971-2271'
        crm = '(71) 99971-2271'
        self.assertTrue(telefones_equivalentes(whatsapp, crm))
        self.assertTrue(telefones_equivalentes('557199712271', crm))
        self.assertTrue(telefones_equivalentes('7199712271', '71999712271'))

    def test_formatacao_espacos_tracos_parenteses(self):
        formatos = [
            '(44) 99988-7766',
            '44 99988-7766',
            '44 9 9988-7766',
            '+55 (44) 99988-7766',
            '+55 44 99988 7766',
            '55 44 99988-7766',
        ]
        referencia = '5544999887766'
        for fmt in formatos:
            with self.subTest(fmt=fmt):
                self.assertTrue(
                    telefones_equivalentes(fmt, referencia),
                    f'{fmt!r} deveria equivaler a {referencia!r}',
                )

    def test_celular_vs_fixo_nao_cruzam(self):
        celular = '(44) 99988-7766'
        fixo = '(44) 3434-5678'
        self.assertFalse(telefones_equivalentes(celular, fixo))
        self.assertTrue(telefones_equivalentes(fixo, '+55 44 3434-5678'))
        self.assertTrue(telefones_equivalentes(fixo, '4434345678'))

    def test_numeros_diferentes_nao_equivalem(self):
        self.assertFalse(telefones_equivalentes('7199712271', '7199712272'))
        self.assertFalse(telefones_equivalentes('44999887766', '44999887755'))

    def test_sufixo8_formato_crm_sem_nono_explicito(self):
        """WhatsApp +554499000-0000 ↔ CRM 4499000-0000 (8 dígitos após DDD)."""
        casos = [
            ('+554499000-0000', '4499000-0000'),
            ('+55 44 99000-0000', '(44) 99000-0000'),
            ('554499000000', '4499000000'),
        ]
        for whatsapp, crm in casos:
            with self.subTest(whatsapp=whatsapp, crm=crm):
                self.assertTrue(telefones_equivalentes(whatsapp, crm))
                sa = sufixos8_comparacao(whatsapp)
                sb = sufixos8_comparacao(crm)
                self.assertTrue(sa & sb, f'sufixos8 deveriam intersectar: {sa!r} & {sb!r}')

    def test_sufixo8_nono_digito_whatsapp_vs_crm(self):
        """9971-2271 (sem 9) ↔ 99971-2271 no CRM via variante + sufixo8."""
        self.assertTrue(telefones_equivalentes('+55 71 9971-2271', '(71) 99971-2271'))
        self.assertIn('99712271', sufixos8_comparacao('7199712271'))
        self.assertIn('99712271', sufixos8_comparacao('71999712271'))

    def test_campo_crm_multiplos_telefones(self):
        campo = '(71) 99971-2271 / (71) 3333-4444'
        partes = extrair_partes_telefone_crm(campo)
        self.assertEqual(len(partes), 2)

        chaves = variantes_telefones_crm(campo)
        self.assertTrue(chaves & variantes_chave_telefone('557199712271'))
        self.assertTrue(chaves & variantes_chave_telefone('7133334444'))
        self.assertFalse(chaves & variantes_chave_telefone('11999999999'))

    def test_separadores_crm(self):
        for sep in ['/', ';', ',', '|']:
            campo = f'(44) 99988-7766{sep}(44) 3434-5678'
            with self.subTest(sep=sep):
                chaves = variantes_telefones_crm(campo)
                self.assertTrue(chaves & variantes_chave_telefone('44999887766'))
                self.assertTrue(chaves & variantes_chave_telefone('4434345678'))


class BuscarClientePorTelefoneTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_tel',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.celular = Cliente.objects.create(
            nome='Loja Celular',
            vendedor=cls.vendedor,
            telefone='(44) 99988-7766',
        )
        cls.fixo = Cliente.objects.create(
            nome='Loja Fixo',
            vendedor=cls.vendedor,
            telefone='(44) 3434-5678',
        )
        cls.multi = Cliente.objects.create(
            nome='Loja Multi Tel',
            vendedor=cls.vendedor,
            telefone='(71) 3333-4444 / (71) 99971-2271',
        )
        cls.duplicado_menor = Cliente.objects.create(
            nome='Duplicado A',
            vendedor=cls.vendedor,
            telefone='(11) 97777-6666',
        )
        cls.duplicado_maior = Cliente.objects.create(
            nome='Duplicado B',
            vendedor=cls.vendedor,
            telefone='(11) 97777-6666',
        )
        cls.semNonoExplicito = Cliente.objects.create(
            nome='Loja Sem Nono',
            vendedor=cls.vendedor,
            telefone='4499000-0000',
        )
        _, cls.token_raw = ExtensionApiToken.gerar_para_usuario(cls.vendedor)

    def _buscar(self, telefone):
        return buscar_cliente_por_telefone(self.vendedor, telefone)

    def test_busca_com_ddi(self):
        self.assertEqual(self._buscar('+55 44 99988-7766'), self.celular)

    def test_busca_sem_ddi(self):
        self.assertEqual(self._buscar('4434345678'), self.fixo)

    def test_busca_formato_whatsapp(self):
        self.assertEqual(self._buscar('+55 71 9971-2271'), self.multi)
        self.assertEqual(self._buscar('557199712271'), self.multi)

    def test_busca_sufixo8_crm_sem_nono_explicito(self):
        self.assertEqual(self._buscar('+554499000-0000'), self.semNonoExplicito)
        self.assertEqual(self._buscar('+55 44 99000-0000'), self.semNonoExplicito)

    def test_busca_segundo_telefone_campo_multiplo(self):
        self.assertEqual(self._buscar('7133334444'), self.multi)
        self.assertEqual(self._buscar('(71) 3333-4444'), self.multi)

    def test_celular_nao_retorna_fixo(self):
        self.assertNotEqual(self._buscar('44999887766'), self.fixo)

    def test_numero_nao_cadastrado(self):
        self.assertIsNone(self._buscar('5511999999999'))
        self.assertIsNone(self._buscar(''))

    def test_duplicata_retorna_menor_pk(self):
        found = self._buscar('11977776666')
        self.assertIsNotNone(found)
        self.assertEqual(found.pk, self.duplicado_menor.pk)
        self.assertEqual(found.nome, 'Duplicado A')

    def test_api_contexto_cenarios(self):
        auth = {'HTTP_AUTHORIZATION': f'Bearer {self.token_raw}'}
        casos_ok = [
            ('5544999887766', 'Loja Celular'),
            ('4434345678', 'Loja Fixo'),
            ('+55 71 9971-2271', 'Loja Multi Tel'),
            ('7133334444', 'Loja Multi Tel'),
        ]
        for telefone, nome_esperado in casos_ok:
            with self.subTest(telefone=telefone):
                resp = self.client.get(
                    reverse('extension:contexto'),
                    {'telefone': telefone},
                    **auth,
                )
                data = resp.json()
                self.assertTrue(data['encontrado'], data)
                self.assertEqual(data['cliente']['nome'], nome_esperado)

        resp = self.client.get(
            reverse('extension:contexto'),
            {'telefone': '5511888888888'},
            **auth,
        )
        self.assertFalse(resp.json()['encontrado'])


@skipIf(not shutil.which('node'), 'Node.js não disponível')
class TelefoneJsParityTests(SimpleTestCase):
    def test_telefone_utils_js(self):
        script = Path(settings.BASE_DIR) / 'chrome-extension' / 'test-telefone.mjs'
        result = subprocess.run(
            ['node', str(script)],
            cwd=settings.BASE_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            0,
            (result.stderr or result.stdout or 'test-telefone.mjs falhou'),
        )
