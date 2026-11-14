from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Trim
from django.db.models.lookups import Exact


def validar_texto_nao_vazio(valor):
    """Impede textos vazios ou formados apenas por espaços."""
    if not valor or not valor.strip():
        raise ValidationError('Este campo não pode ficar vazio.')


class Produto(models.Model):
    nome = models.CharField(
        'nome',
        max_length=150,
        validators=[validar_texto_nao_vazio],
    )
    descricao = models.TextField('descrição', blank=True)
    categoria = models.CharField(
        'categoria',
        max_length=100,
        validators=[validar_texto_nao_vazio],
    )
    preco = models.DecimalField(
        'preço',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'), 'O preço não pode ser negativo.')],
    )
    quantidade_estoque = models.PositiveIntegerField(
        'quantidade em estoque',
        default=0,
    )
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'produto'
        verbose_name_plural = 'produtos'
        ordering = ['nome']
        # Regras também garantidas pelo próprio banco de dados.
        constraints = [
            models.CheckConstraint(
                condition=~Q(Exact(Trim('nome'), '')),
                name='produto_nome_nao_vazio',
                violation_error_message='O nome do produto não pode ficar vazio.',
            ),
            models.CheckConstraint(
                condition=Q(preco__gte=0),
                name='produto_preco_nao_negativo',
                violation_error_message='O preço não pode ser negativo.',
            ),
            models.CheckConstraint(
                condition=Q(quantidade_estoque__gte=0),
                name='produto_estoque_nao_negativo',
                violation_error_message='A quantidade em estoque não pode ser negativa.',
            ),
        ]

    def __str__(self):
        return self.nome

    def clean(self):
        # Remove espaços extras no início e no fim dos textos.
        if self.nome:
            self.nome = self.nome.strip()
        if self.categoria:
            self.categoria = self.categoria.strip()


class MovimentacaoEstoque(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'

    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,  # Não permite excluir produto com histórico.
        related_name='movimentacoes',
        verbose_name='produto',
    )
    tipo = models.CharField('tipo', max_length=7, choices=Tipo.choices)
    quantidade = models.PositiveIntegerField(
        'quantidade',
        validators=[MinValueValidator(1, 'A quantidade deve ser maior que zero.')],
    )
    data_movimentacao = models.DateTimeField('data da movimentação', auto_now_add=True)
    observacao = models.TextField('observação', blank=True)

    class Meta:
        verbose_name = 'movimentação de estoque'
        verbose_name_plural = 'movimentações de estoque'
        ordering = ['-data_movimentacao']
        constraints = [
            models.CheckConstraint(
                condition=Q(quantidade__gt=0),
                name='movimentacao_quantidade_positiva',
                violation_error_message='A quantidade deve ser maior que zero.',
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=['ENTRADA', 'SAIDA']),
                name='movimentacao_tipo_valido',
                violation_error_message='Tipo de movimentação inválido.',
            ),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} de {self.quantidade} - {self.produto}'
