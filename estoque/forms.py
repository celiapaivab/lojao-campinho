from decimal import Decimal

from django import forms

from .models import MovimentacaoEstoque, Produto


class ProdutoForm(forms.Form):
    """Formulário para cadastrar um novo produto."""

    nome = forms.CharField(label='Produto', max_length=150)
    categoria = forms.CharField(label='Categoria', max_length=100)
    preco = forms.DecimalField(
        label='Preço (R$)',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        localize=True,  # Aceita o formato brasileiro, ex.: 12,50
        error_messages={'min_value': 'O preço não pode ser negativo.'},
    )
    quantidade_estoque = forms.IntegerField(
        label='Quantidade inicial',
        min_value=0,
        initial=0,
        error_messages={'min_value': 'A quantidade não pode ser negativa.'},
    )


class ProdutoChoiceField(forms.ModelChoiceField):
    """Lista de produtos mostrando também o estoque atual."""

    def label_from_instance(self, produto):
        return f'{produto.nome} (estoque: {produto.quantidade_estoque})'


class MovimentacaoForm(forms.Form):
    """Formulário para registrar uma entrada ou saída de estoque."""

    produto = ProdutoChoiceField(
        label='Produto',
        queryset=Produto.objects.all(),
        empty_label='Selecione um produto',
    )
    tipo = forms.ChoiceField(
        label='Tipo de movimentação',
        choices=MovimentacaoEstoque.Tipo.choices,
    )
    quantidade = forms.IntegerField(
        label='Quantidade',
        min_value=1,
        error_messages={'min_value': 'A quantidade deve ser maior que zero.'},
    )
    observacao = forms.CharField(
        label='Observação (opcional)',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
    )
