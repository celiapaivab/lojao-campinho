from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from .models import MovimentacaoEstoque, Produto
from .services import cadastrar_produto, registrar_movimentacao

ENTRADA = MovimentacaoEstoque.Tipo.ENTRADA
SAIDA = MovimentacaoEstoque.Tipo.SAIDA


class ProdutoTests(TestCase):
    def criar_produto(self, **dados):
        valores = {
            'nome': 'Caderno 10 matérias',
            'categoria': 'Cadernos',
            'preco': Decimal('25.90'),
            'quantidade_estoque': 10,
        }
        valores.update(dados)
        return Produto(**valores)

    def test_produto_valido(self):
        produto = self.criar_produto()
        produto.full_clean()
        produto.save()
        self.assertEqual(str(produto), 'Caderno 10 matérias')
        self.assertTrue(produto.ativo)

    def test_nome_com_espacos_extras_e_ajustado(self):
        produto = self.criar_produto(nome='  Lápis  ')
        produto.full_clean()
        self.assertEqual(produto.nome, 'Lápis')

    def test_nome_vazio_ou_so_espacos_e_invalido(self):
        for nome in ['', '   ']:
            with self.assertRaises(ValidationError):
                self.criar_produto(nome=nome).full_clean()

    def test_preco_negativo_e_invalido(self):
        with self.assertRaises(ValidationError):
            self.criar_produto(preco=Decimal('-1.00')).full_clean()

    def test_estoque_negativo_e_invalido(self):
        with self.assertRaises(ValidationError):
            self.criar_produto(quantidade_estoque=-1).full_clean()

    def test_banco_rejeita_valores_invalidos(self):
        # Mesmo salvando sem full_clean(), o banco bloqueia os valores.
        for dados in [{'nome': '   '}, {'preco': Decimal('-1.00')}, {'quantidade_estoque': -1}]:
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    self.criar_produto(**dados).save()


class MovimentacaoEstoqueTests(TestCase):
    def setUp(self):
        self.produto = Produto.objects.create(
            nome='Borracha', categoria='Escrita', preco=Decimal('2.50')
        )

    def test_movimentacao_valida(self):
        mov = MovimentacaoEstoque(
            produto=self.produto, tipo=MovimentacaoEstoque.Tipo.ENTRADA, quantidade=5
        )
        mov.full_clean()
        mov.save()
        self.assertIsNotNone(mov.data_movimentacao)
        self.assertEqual(str(mov), 'Entrada de 5 - Borracha')

    def test_quantidade_zero_e_invalida(self):
        mov = MovimentacaoEstoque(
            produto=self.produto, tipo=MovimentacaoEstoque.Tipo.SAIDA, quantidade=0
        )
        with self.assertRaises(ValidationError):
            mov.full_clean()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                mov.save()

    def test_tipo_invalido(self):
        mov = MovimentacaoEstoque(produto=self.produto, tipo='TROCA', quantidade=1)
        with self.assertRaises(ValidationError):
            mov.full_clean()

    def test_movimentacao_exige_produto(self):
        mov = MovimentacaoEstoque(tipo=MovimentacaoEstoque.Tipo.ENTRADA, quantidade=1)
        with self.assertRaises(ValidationError):
            mov.full_clean()

    def test_produto_com_historico_nao_pode_ser_excluido(self):
        MovimentacaoEstoque.objects.create(
            produto=self.produto, tipo=MovimentacaoEstoque.Tipo.ENTRADA, quantidade=3
        )
        with self.assertRaises(ProtectedError):
            self.produto.delete()
        self.assertTrue(Produto.objects.filter(pk=self.produto.pk).exists())

    def test_produto_sem_historico_pode_ser_excluido(self):
        self.produto.delete()
        self.assertFalse(Produto.objects.exists())


class CadastrarProdutoTests(TestCase):
    def test_cadastra_produto_valido(self):
        produto = cadastrar_produto(
            nome='Caneta azul', categoria='Escrita', preco=Decimal('3.50'), quantidade_estoque=20
        )
        salvo = Produto.objects.get(pk=produto.pk)
        self.assertEqual(salvo.nome, 'Caneta azul')
        self.assertEqual(salvo.categoria, 'Escrita')
        self.assertEqual(salvo.preco, Decimal('3.50'))
        self.assertEqual(salvo.quantidade_estoque, 20)
        self.assertTrue(salvo.ativo)

    def test_rejeita_produto_invalido(self):
        dados_validos = {
            'nome': 'Régua 30 cm', 'categoria': 'Geometria',
            'preco': Decimal('4.00'), 'quantidade_estoque': 5,
        }
        dados_invalidos = [
            {'nome': ''},
            {'nome': '   '},
            {'categoria': ''},
            {'preco': None},
            {'preco': Decimal('-0.01')},
            {'quantidade_estoque': -1},
            {'quantidade_estoque': None},
        ]
        for alteracao in dados_invalidos:
            with self.subTest(alteracao=alteracao):
                with self.assertRaises(ValidationError):
                    cadastrar_produto(**{**dados_validos, **alteracao})
        self.assertFalse(Produto.objects.exists())


class RegistrarMovimentacaoTests(TestCase):
    def setUp(self):
        self.produto = cadastrar_produto(
            nome='Lápis HB', categoria='Escrita', preco=Decimal('1.20'), quantidade_estoque=10
        )

    def estoque_no_banco(self):
        return Produto.objects.get(pk=self.produto.pk).quantidade_estoque

    def test_entrada_aumenta_estoque(self):
        registrar_movimentacao(self.produto, ENTRADA, 5)
        self.assertEqual(self.estoque_no_banco(), 15)
        self.assertEqual(self.produto.quantidade_estoque, 15)

    def test_saida_diminui_estoque(self):
        registrar_movimentacao(self.produto, SAIDA, 4)
        self.assertEqual(self.estoque_no_banco(), 6)
        self.assertEqual(self.produto.quantidade_estoque, 6)

    def test_saida_de_todo_o_estoque_e_permitida(self):
        registrar_movimentacao(self.produto, SAIDA, 10)
        self.assertEqual(self.estoque_no_banco(), 0)

    def test_saida_maior_que_estoque_e_rejeitada(self):
        with self.assertRaises(ValidationError) as erro:
            registrar_movimentacao(self.produto, SAIDA, 11)
        self.assertIn('Estoque insuficiente', str(erro.exception))
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_quantidade_zero_ou_negativa_e_rejeitada(self):
        for tipo in [ENTRADA, SAIDA]:
            for quantidade in [0, -1, -5]:
                with self.subTest(tipo=tipo, quantidade=quantidade):
                    with self.assertRaises(ValidationError):
                        registrar_movimentacao(self.produto, tipo, quantidade)
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_tipo_invalido_e_rejeitado(self):
        for tipo in ['TROCA', '', 'entrada', None]:
            with self.subTest(tipo=tipo):
                with self.assertRaises(ValidationError):
                    registrar_movimentacao(self.produto, tipo, 1)
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_produto_inexistente_e_rejeitado(self):
        produto_nao_salvo = Produto(nome='Cola', categoria='Escritório', preco=Decimal('5.00'))
        with self.assertRaises(ValidationError):
            registrar_movimentacao(produto_nao_salvo, ENTRADA, 1)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_movimentacoes_com_sucesso_ficam_no_historico(self):
        entrada = registrar_movimentacao(self.produto, ENTRADA, 3, observacao='Compra do fornecedor')
        saida = registrar_movimentacao(self.produto, SAIDA, 2)

        historico = self.produto.movimentacoes.order_by('pk')
        self.assertEqual(list(historico), [entrada, saida])
        self.assertEqual(entrada.tipo, ENTRADA)
        self.assertEqual(entrada.quantidade, 3)
        self.assertEqual(entrada.observacao, 'Compra do fornecedor')
        self.assertIsNotNone(entrada.data_movimentacao)
        self.assertEqual(saida.tipo, SAIDA)
        self.assertEqual(saida.quantidade, 2)

    def test_falha_ao_gravar_historico_desfaz_alteracao_do_estoque(self):
        # Simula um erro ao salvar a movimentação, depois que o estoque já
        # foi atualizado: a transação deve desfazer a alteração do estoque.
        with mock.patch.object(MovimentacaoEstoque, 'save', side_effect=RuntimeError('falha simulada')):
            with self.assertRaises(RuntimeError):
                registrar_movimentacao(self.produto, ENTRADA, 5)
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_objeto_desatualizado_nao_sobrescreve_estoque(self):
        # Duas referências ao mesmo produto, como em duas telas abertas.
        outra_referencia = Produto.objects.get(pk=self.produto.pk)
        registrar_movimentacao(self.produto, SAIDA, 6)  # estoque: 4
        # outra_referencia ainda "acha" que há 10 em estoque.
        with self.assertRaises(ValidationError):
            registrar_movimentacao(outra_referencia, SAIDA, 6)
        registrar_movimentacao(outra_referencia, ENTRADA, 1)
        self.assertEqual(self.estoque_no_banco(), 5)

    def test_sequencia_de_movimentacoes_gera_estoque_final_correto(self):
        registrar_movimentacao(self.produto, ENTRADA, 15)   # 25
        registrar_movimentacao(self.produto, SAIDA, 7)      # 18
        registrar_movimentacao(self.produto, SAIDA, 3)      # 15
        with self.assertRaises(ValidationError):
            registrar_movimentacao(self.produto, SAIDA, 16)  # rejeitada
        registrar_movimentacao(self.produto, ENTRADA, 2)    # 17
        registrar_movimentacao(self.produto, SAIDA, 17)     # 0

        self.assertEqual(self.estoque_no_banco(), 0)
        self.assertEqual(self.produto.movimentacoes.count(), 5)
