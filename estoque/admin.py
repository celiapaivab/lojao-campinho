from django.contrib import admin

from .models import MovimentacaoEstoque, Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'categoria', 'preco', 'quantidade_estoque', 'ativo']
    list_filter = ['categoria', 'ativo']
    search_fields = ['nome']


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ['produto', 'tipo', 'quantidade', 'data_movimentacao']
    list_filter = ['tipo']
