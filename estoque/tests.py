from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse

from .models import MovimentacaoEstoque, Produto
from .services import cadastrar_produto, registrar_movimentacao

ENTRADA = MovimentacaoEstoque.Tipo.ENTRADA
SAIDA = MovimentacaoEstoque.Tipo.SAIDA

# Usuário e senha usados apenas no banco temporário dos testes.
USUARIO_TESTE = 'dono_teste'
SENHA_TESTE = 'senha-so-para-testes-123'


class TesteComUsuarioLogado(TestCase):
    """Base para testes das telas: cria um usuário e já faz o login."""

    def setUp(self):
        self.usuario = User.objects.create_user(username=USUARIO_TESTE, password=SENHA_TESTE)
        self.client.force_login(self.usuario)


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


class PaginaInicialTests(TesteComUsuarioLogado):
    def test_pagina_inicial_carrega(self):
        resposta = self.client.get(reverse('estoque:inicio'))
        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'estoque/inicio.html')
        self.assertContains(resposta, 'Bem-vindo')
        self.assertContains(resposta, f'href="{reverse("estoque:gerenciar")}"')

    def test_mostra_total_de_produtos(self):
        cadastrar_produto(nome='Caneta', categoria='Escrita', preco=Decimal('2.00'))
        cadastrar_produto(nome='Lápis', categoria='Escrita', preco=Decimal('1.00'))
        resposta = self.client.get(reverse('estoque:inicio'))
        self.assertEqual(resposta.context['total_produtos'], 2)
        self.assertContains(resposta, 'Produtos cadastrados: <strong>2</strong>', html=True)

    def test_navegacao_presente_e_links_funcionam(self):
        paginas = ['estoque:inicio', 'estoque:gerenciar', 'estoque:consultar']
        for pagina in paginas:
            with self.subTest(pagina=pagina):
                resposta = self.client.get(reverse(pagina))
                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, 'Lojão do Campinho')
                for destino in paginas:
                    self.assertContains(resposta, f'href="{reverse(destino)}"')
                    self.assertEqual(self.client.get(reverse(destino)).status_code, 200)


class GerenciarEstoqueTests(TesteComUsuarioLogado):
    def setUp(self):
        super().setUp()
        self.url = reverse('estoque:gerenciar')
        self.produto = cadastrar_produto(
            nome='Caderno', categoria='Cadernos', preco=Decimal('15.00'), quantidade_estoque=10
        )

    def estoque_no_banco(self):
        return Produto.objects.get(pk=self.produto.pk).quantidade_estoque

    def movimentar(self, tipo, quantidade, produto=None):
        return self.client.post(self.url, {
            'acao': 'movimentar',
            'produto': (produto or self.produto).pk,
            'tipo': tipo,
            'quantidade': quantidade,
            'observacao': '',
        }, follow=True)

    def test_pagina_carrega_com_as_duas_operacoes(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Cadastrar produto')
        self.assertContains(resposta, 'Movimentar estoque')
        self.assertContains(resposta, 'Salvar')
        self.assertContains(resposta, 'Cancelar')
        resposta = self.client.get(self.url + '?acao=movimentar')
        self.assertContains(resposta, 'Tipo de movimentação')

    def test_cadastra_produto_pelo_formulario(self):
        resposta = self.client.post(self.url, {
            'acao': 'cadastrar', 'nome': 'Mochila', 'categoria': 'Acessórios',
            'preco': '89,90', 'quantidade_estoque': '3',
        }, follow=True)
        self.assertRedirects(resposta, self.url)
        produto = Produto.objects.get(nome='Mochila')
        self.assertEqual(produto.preco, Decimal('89.90'))
        self.assertEqual(produto.quantidade_estoque, 3)
        self.assertContains(resposta, 'Produto &quot;Mochila&quot; cadastrado com sucesso.')

    def test_cadastro_invalido_nao_salva(self):
        dados_invalidos = [
            {'nome': '', 'categoria': 'X', 'preco': '1,00', 'quantidade_estoque': '1'},
            {'nome': '   ', 'categoria': 'X', 'preco': '1,00', 'quantidade_estoque': '1'},
            {'nome': 'Cola', 'categoria': 'X', 'preco': '-1,00', 'quantidade_estoque': '1'},
            {'nome': 'Cola', 'categoria': 'X', 'preco': '1,00', 'quantidade_estoque': '-1'},
            {'nome': 'Cola', 'categoria': 'X', 'preco': 'abc', 'quantidade_estoque': '1'},
        ]
        for dados in dados_invalidos:
            with self.subTest(dados=dados):
                resposta = self.client.post(self.url, {'acao': 'cadastrar', **dados})
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta.context['form_produto'].errors)
        self.assertEqual(Produto.objects.count(), 1)

    def test_entrada_pelo_formulario(self):
        resposta = self.movimentar('ENTRADA', 5)
        self.assertRedirects(resposta, self.url + '?acao=movimentar')
        self.assertEqual(self.estoque_no_banco(), 15)
        self.assertContains(resposta, 'Estoque atual: 15.')
        self.assertEqual(MovimentacaoEstoque.objects.count(), 1)

    def test_saida_pelo_formulario(self):
        resposta = self.movimentar('SAIDA', 4)
        self.assertRedirects(resposta, self.url + '?acao=movimentar')
        self.assertEqual(self.estoque_no_banco(), 6)
        self.assertContains(resposta, 'Estoque atual: 6.')

    def test_saida_maior_que_estoque_e_rejeitada(self):
        resposta = self.movimentar('SAIDA', 11)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Estoque insuficiente para esta saída.')
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())

    def test_movimentacao_invalida_nao_altera_estoque(self):
        casos = [
            {'tipo': 'ENTRADA', 'quantidade': 0},
            {'tipo': 'SAIDA', 'quantidade': -2},
            {'tipo': 'TROCA', 'quantidade': 1},
            {'tipo': 'ENTRADA', 'quantidade': ''},
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                resposta = self.movimentar(**caso)
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta.context['form_movimentacao'].errors)
        resposta = self.client.post(self.url, {
            'acao': 'movimentar', 'produto': '9999', 'tipo': 'ENTRADA', 'quantidade': 1,
        })
        self.assertTrue(resposta.context['form_movimentacao'].errors)
        self.assertEqual(self.estoque_no_banco(), 10)
        self.assertFalse(MovimentacaoEstoque.objects.exists())


class ConsultarEstoqueTests(TesteComUsuarioLogado):
    def test_sem_produtos_mostra_mensagem(self):
        resposta = self.client.get(reverse('estoque:consultar'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Nenhum produto cadastrado ainda.')
        self.assertNotContains(resposta, '<table')

    def test_mostra_valores_e_situacao_do_estoque(self):
        cadastrar_produto(nome='Apontador', categoria='Escrita', preco=Decimal('3.50'), quantidade_estoque=5)
        cadastrar_produto(nome='Borracha', categoria='Escrita', preco=Decimal('2.00'), quantidade_estoque=6)
        cadastrar_produto(nome='Cola', categoria='Escrita', preco=Decimal('4.25'), quantidade_estoque=0)

        resposta = self.client.get(reverse('estoque:consultar'))
        self.assertEqual(resposta.status_code, 200)
        for coluna in ['Produto', 'Preço', 'Quantidade', 'Situação do Estoque']:
            self.assertContains(resposta, f'<th>{coluna}</th>', html=True)

        self.assertContains(resposta, '<td class="preco">R$ 3,50</td>', html=True)
        self.assertContains(resposta, '<td class="preco">R$ 2,00</td>', html=True)
        self.assertContains(resposta, '<td class="preco">R$ 4,25</td>', html=True)
        # 5 e 0 unidades: estoque baixo. 6 unidades: em estoque.
        self.assertContains(resposta, 'Estoque baixo', count=2)
        self.assertContains(resposta, 'Em estoque', count=1)

        conteudo = resposta.content.decode()
        linha_apontador = conteudo.split('Apontador')[1].split('</tr>')[0]
        linha_borracha = conteudo.split('Borracha')[1].split('</tr>')[0]
        self.assertIn('<td>5</td>', linha_apontador)
        self.assertIn('Estoque baixo', linha_apontador)
        self.assertIn('<td>6</td>', linha_borracha)
        self.assertIn('Em estoque', linha_borracha)

    def test_consulta_reflete_movimentacoes(self):
        produto = cadastrar_produto(nome='Tesoura', categoria='Escritório', preco=Decimal('9.90'), quantidade_estoque=8)
        registrar_movimentacao(produto, SAIDA, 3)
        resposta = self.client.get(reverse('estoque:consultar'))
        linha = resposta.content.decode().split('Tesoura')[1].split('</tr>')[0]
        self.assertIn('<td>5</td>', linha)
        self.assertIn('Estoque baixo', linha)


class EstoqueBaixoTests(TestCase):
    def test_limite_de_estoque_baixo(self):
        produto = Produto(nome='Giz', categoria='Escrita', preco=Decimal('1.00'))
        for quantidade, esperado in [(0, True), (5, True), (6, False), (50, False)]:
            with self.subTest(quantidade=quantidade):
                produto.quantidade_estoque = quantidade
                self.assertEqual(produto.estoque_baixo, esperado)


class AutenticacaoTests(TestCase):
    PAGINAS = ['estoque:inicio', 'estoque:gerenciar', 'estoque:consultar']

    def setUp(self):
        self.usuario = User.objects.create_user(username=USUARIO_TESTE, password=SENHA_TESTE)
        self.url_login = reverse('login')
        self.url_logout = reverse('logout')

    def fazer_login(self, senha=SENHA_TESTE, **extras):
        return self.client.post(
            self.url_login, {'username': USUARIO_TESTE, 'password': senha, **extras}
        )

    def esta_logado(self):
        return '_auth_user_id' in self.client.session

    def test_visitante_e_redirecionado_para_login(self):
        for pagina in self.PAGINAS:
            with self.subTest(pagina=pagina):
                url = reverse(pagina)
                resposta = self.client.get(url)
                self.assertRedirects(resposta, f'{self.url_login}?next={url}')

    def test_visitante_nao_consegue_cadastrar_produto(self):
        resposta = self.client.post(reverse('estoque:gerenciar'), {
            'acao': 'cadastrar', 'nome': 'Cola', 'categoria': 'X',
            'preco': '1,00', 'quantidade_estoque': '1',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Produto.objects.exists())

    def test_pagina_de_login(self):
        resposta = self.client.get(self.url_login)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Usuário')
        self.assertContains(resposta, 'Senha')
        self.assertContains(resposta, '<button type="submit" class="botao botao-principal">Entrar</button>', html=True)
        self.assertContains(resposta, 'csrfmiddlewaretoken')
        # Sem login, a barra mostra só o nome da loja (sem links nem "Sair").
        self.assertNotContains(resposta, 'Gerenciar Estoque')
        self.assertNotContains(resposta, 'Sair')

    def test_login_valido_redireciona_para_inicio(self):
        resposta = self.fazer_login()
        self.assertRedirects(resposta, reverse('estoque:inicio'))
        self.assertTrue(self.esta_logado())

    def test_login_valido_volta_para_pagina_pedida(self):
        destino = reverse('estoque:consultar')
        resposta = self.fazer_login(next=destino)
        self.assertRedirects(resposta, destino)

    def test_login_invalido_falha(self):
        resposta = self.fazer_login(senha='senha-errada')
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'entre com um usuário')
        self.assertFalse(self.esta_logado())

        resposta = self.client.post(self.url_login, {'username': '', 'password': ''})
        self.assertContains(resposta, 'Este campo é obrigatório.', count=2)
        self.assertFalse(self.esta_logado())

    def test_usuario_logado_acessa_as_tres_paginas(self):
        self.fazer_login()
        for pagina in self.PAGINAS:
            with self.subTest(pagina=pagina):
                resposta = self.client.get(reverse(pagina))
                self.assertEqual(resposta.status_code, 200)
                self.assertContains(resposta, 'Sair')

    def test_usuario_logado_ao_abrir_login_vai_para_inicio(self):
        self.fazer_login()
        resposta = self.client.get(self.url_login)
        self.assertRedirects(resposta, reverse('estoque:inicio'))

    def test_usuario_logado_cadastra_produto_e_movimenta_estoque(self):
        self.fazer_login()
        url = reverse('estoque:gerenciar')
        self.client.post(url, {
            'acao': 'cadastrar', 'nome': 'Estojo', 'categoria': 'Acessórios',
            'preco': '19,90', 'quantidade_estoque': '7',
        })
        produto = Produto.objects.get(nome='Estojo')
        self.client.post(url, {
            'acao': 'movimentar', 'produto': produto.pk, 'tipo': 'SAIDA', 'quantidade': '3',
        })
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_estoque, 4)
        self.assertEqual(produto.movimentacoes.count(), 1)

    def test_logout_encerra_a_sessao(self):
        self.fazer_login()
        resposta = self.client.post(self.url_logout)
        self.assertRedirects(resposta, self.url_login)
        self.assertFalse(self.esta_logado())

    def test_paginas_bloqueadas_depois_do_logout(self):
        self.fazer_login()
        self.client.post(self.url_logout)
        for pagina in self.PAGINAS:
            with self.subTest(pagina=pagina):
                url = reverse(pagina)
                self.assertRedirects(self.client.get(url), f'{self.url_login}?next={url}')

    def test_get_no_logout_nao_desloga(self):
        self.fazer_login()
        resposta = self.client.get(self.url_logout)
        self.assertEqual(resposta.status_code, 405)  # Método não permitido
        self.assertTrue(self.esta_logado())
        self.assertEqual(self.client.get(reverse('estoque:inicio')).status_code, 200)

    def test_senha_guardada_com_hash(self):
        self.assertNotEqual(self.usuario.password, SENHA_TESTE)
        self.assertTrue(self.usuario.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(self.usuario.check_password(SENHA_TESTE))


class ProtecaoCsrfTests(TestCase):
    """Com a verificação de CSRF ligada, POST sem token é recusado (403)."""

    def setUp(self):
        self.usuario = User.objects.create_user(username=USUARIO_TESTE, password=SENHA_TESTE)
        self.client = Client(enforce_csrf_checks=True)

    def test_login_sem_token_e_recusado(self):
        resposta = self.client.post(
            reverse('login'), {'username': USUARIO_TESTE, 'password': SENHA_TESTE}
        )
        self.assertEqual(resposta.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_formularios_sem_token_sao_recusados(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('estoque:gerenciar'), {
            'acao': 'cadastrar', 'nome': 'Cola', 'categoria': 'X',
            'preco': '1,00', 'quantidade_estoque': '1',
        })
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(Produto.objects.exists())

        resposta = self.client.post(reverse('logout'))
        self.assertEqual(resposta.status_code, 403)
        self.assertIn('_auth_user_id', self.client.session)

    def test_formulario_com_token_e_aceito(self):
        self.client.force_login(self.usuario)
        url = reverse('estoque:gerenciar')
        self.client.get(url)  # A página entrega o cookie com o token CSRF.
        token = self.client.cookies['csrftoken'].value
        resposta = self.client.post(url, {
            'csrfmiddlewaretoken': token, 'acao': 'cadastrar', 'nome': 'Cola',
            'categoria': 'X', 'preco': '1,00', 'quantidade_estoque': '1',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Produto.objects.filter(nome='Cola').exists())
