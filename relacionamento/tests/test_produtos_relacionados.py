from django.test import TestCase

from accounts.models import Papel, Usuario
from clientes.models import Cliente, Produto, TipoProduto
from comissoes.services.produtividade import _atividades_base
from relacionamento.models import AtividadeCliente, Resultado, TipoContato
from relacionamento.services.atividades import registrar_interacao
from relacionamento.services.editar_atividade import editar_atividade


class ProdutosRelacionadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.vendedor = Usuario.objects.create_user(
            username='vendedor_prod',
            password='testpass123',
            papel=Papel.VENDEDOR,
        )
        cls.cliente = Cliente.objects.create(vendedor=cls.vendedor, nome='Cliente Produtos')
        cls.produto_a = Produto.objects.create(nome='DAY BED FLORES', tipo_produto=TipoProduto.PADRAO)
        cls.produto_b = Produto.objects.create(nome='SOFA TOSCANA', tipo_produto=TipoProduto.PADRAO)

    def test_registrar_interacao_com_multiplos_produtos(self):
        atividade = registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.NEGOCIACAO,
            resumo='Negociação com dois produtos',
            resultado=Resultado.INTERESSADO,
            produtos_relacionados=[self.produto_a, self.produto_b],
        )
        nomes = set(atividade.produtos_relacionados.values_list('nome', flat=True))
        self.assertEqual(nomes, {'DAY BED FLORES', 'SOFA TOSCANA'})

    def test_filtro_por_produto_retorna_interacao(self):
        atividade = registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.NEGOCIACAO,
            resumo='Dois produtos na mesma interação',
            resultado=Resultado.INTERESSADO,
            produtos_relacionados=[self.produto_a, self.produto_b],
        )
        qs_a = _atividades_base(self.vendedor, produto_id=self.produto_a.pk)
        qs_b = _atividades_base(self.vendedor, produto_id=self.produto_b.pk)
        self.assertIn(atividade.pk, list(qs_a.values_list('pk', flat=True)))
        self.assertIn(atividade.pk, list(qs_b.values_list('pk', flat=True)))

    def test_filtro_por_produto_nao_duplica_contagem(self):
        registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.NEGOCIACAO,
            resumo='Dois produtos na mesma interação',
            resultado=Resultado.INTERESSADO,
            produtos_relacionados=[self.produto_a, self.produto_b],
        )
        qs = _atividades_base(self.vendedor, produto_id=self.produto_a.pk)
        self.assertEqual(qs.count(), 1)

    def test_editar_produtos_gera_audit_log(self):
        atividade = registrar_interacao(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.NEGOCIACAO,
            resumo='Um produto inicial',
            resultado=Resultado.INTERESSADO,
            produtos_relacionados=[self.produto_a],
        )
        edicao = editar_atividade(
            atividade,
            self.vendedor,
            {'produtos_relacionados': [self.produto_a, self.produto_b]},
        )
        self.assertIsNotNone(edicao)
        produto_log = next(a for a in edicao.alteracoes if a['campo'] == 'produtos_relacionados')
        self.assertIn('DAY BED FLORES', produto_log['antes'])
        self.assertIn('SOFA TOSCANA', produto_log['depois'])
        atividade.refresh_from_db()
        self.assertEqual(atividade.produtos_relacionados.count(), 2)

    def test_migration_preserva_produto_unico_legado(self):
        atividade = AtividadeCliente.objects.create(
            cliente=self.cliente,
            usuario=self.vendedor,
            tipo_contato=TipoContato.OUTRO,
            resumo='Legado',
            resultado=Resultado.CONTATO_REALIZADO,
            concluida=True,
        )
        atividade.produtos_relacionados.add(self.produto_a)
        self.assertEqual(atividade.produtos_relacionados.get().nome, 'DAY BED FLORES')
