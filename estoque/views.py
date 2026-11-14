from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import MovimentacaoForm, ProdutoForm
from .models import Produto
from .services import cadastrar_produto, registrar_movimentacao


def inicio(request):
    contexto = {'total_produtos': Produto.objects.count()}
    return render(request, 'estoque/inicio.html', contexto)


def gerenciar_estoque(request):
    # A tela tem duas operações: "cadastrar" um produto ou "movimentar" o estoque.
    acao = request.POST.get('acao') or request.GET.get('acao') or 'cadastrar'
    if acao not in ('cadastrar', 'movimentar'):
        acao = 'cadastrar'

    form_produto = ProdutoForm()
    form_movimentacao = MovimentacaoForm()

    if request.method == 'POST':
        if acao == 'cadastrar':
            form_produto = ProdutoForm(request.POST)
            if form_produto.is_valid():
                try:
                    produto = cadastrar_produto(**form_produto.cleaned_data)
                except ValidationError as erro:
                    adicionar_erros(form_produto, erro)
                else:
                    messages.success(request, f'Produto "{produto.nome}" cadastrado com sucesso.')
                    return redirect('estoque:gerenciar')
        else:
            form_movimentacao = MovimentacaoForm(request.POST)
            if form_movimentacao.is_valid():
                dados = form_movimentacao.cleaned_data
                try:
                    movimentacao = registrar_movimentacao(
                        dados['produto'], dados['tipo'], dados['quantidade'], dados['observacao']
                    )
                except ValidationError as erro:
                    adicionar_erros(form_movimentacao, erro)
                else:
                    produto = movimentacao.produto
                    messages.success(
                        request,
                        f'{movimentacao.get_tipo_display()} de {movimentacao.quantidade} '
                        f'unidade(s) de "{produto.nome}" registrada com sucesso. '
                        f'Estoque atual: {produto.quantidade_estoque}.',
                    )
                    return redirect(f"{request.path}?acao=movimentar")

    contexto = {
        'acao': acao,
        'form_produto': form_produto,
        'form_movimentacao': form_movimentacao,
    }
    return render(request, 'estoque/gerenciar.html', contexto)


def consultar_estoque(request):
    contexto = {'produtos': Produto.objects.all()}
    return render(request, 'estoque/consultar.html', contexto)


def adicionar_erros(form, erro):
    """Mostra no formulário os erros de validação vindos dos services."""
    for campo, mensagens in erro.message_dict.items():
        if campo in form.fields:
            form.add_error(campo, mensagens)
        else:
            form.add_error(None, mensagens)
