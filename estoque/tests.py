from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from .models import MovimentacaoEstoque, Produto


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
