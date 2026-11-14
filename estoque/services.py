"""
Regras de negócio do estoque.

Os models (models.py) representam e validam os dados.
Este módulo reúne as operações do dia a dia da loja:
cadastrar produtos e registrar entradas e saídas de estoque.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import MovimentacaoEstoque, Produto


def cadastrar_produto(nome, categoria, preco, quantidade_estoque=0, descricao=''):
    """Valida e salva um novo produto. Retorna o produto criado.

    Lança ValidationError se algum dado for inválido (nada é salvo).
    """
    produto = Produto(
        nome=nome,
        categoria=categoria,
        preco=preco,
        quantidade_estoque=quantidade_estoque,
        descricao=descricao,
    )
    produto.full_clean()  # Executa todas as validações do model.
    produto.save()
    return produto


def registrar_movimentacao(produto, tipo, quantidade, observacao=''):
    """Registra uma entrada ou saída e atualiza o estoque do produto.

    - ENTRADA soma a quantidade ao estoque.
    - SAIDA subtrai a quantidade, desde que haja estoque suficiente.

    Lança ValidationError se a operação for inválida. Nesse caso,
    o estoque não muda e nenhuma movimentação é registrada.
    Retorna a movimentação criada.
    """
    movimentacao = MovimentacaoEstoque(
        produto=produto,
        tipo=tipo,
        quantidade=quantidade,
        observacao=observacao,
    )
    # Valida produto existente, tipo válido e quantidade maior que zero.
    movimentacao.full_clean()
    quantidade = movimentacao.quantidade

    # Tudo dentro do bloco abaixo acontece em uma única transação:
    # se qualquer passo falhar, o banco desfaz todas as alterações.
    with transaction.atomic():
        produtos = Produto.objects.filter(pk=produto.pk)

        # F('quantidade_estoque') faz o cálculo direto no banco de dados,
        # usando o valor atual salvo. Assim, duas operações seguidas não
        # sobrescrevem uma à outra com um valor antigo.
        if tipo == MovimentacaoEstoque.Tipo.ENTRADA:
            produtos.update(quantidade_estoque=F('quantidade_estoque') + quantidade)
        else:
            # Só atualiza se ainda houver estoque suficiente.
            atualizados = produtos.filter(quantidade_estoque__gte=quantidade).update(
                quantidade_estoque=F('quantidade_estoque') - quantidade
            )
            if atualizados == 0:
                raise ValidationError(
                    {'quantidade': 'Estoque insuficiente para esta saída.'}
                )

        movimentacao.save()

    # Atualiza o objeto em memória com o estoque salvo no banco.
    produto.refresh_from_db(fields=['quantidade_estoque'])
    return movimentacao
