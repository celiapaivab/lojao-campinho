# Lojão do Campinho

Aplicação web simples para controle de estoque de uma pequena papelaria
(loja de material escolar). O objetivo é substituir o controle manual de
estoque por um sistema fácil de usar.

Projeto individual da disciplina de Desenvolvimento de Software.

## Tecnologias

- Python 3.12
- Django 5.2 LTS
- SQLite (banco de dados padrão do Django)
- Django Templates, HTML5 e CSS3
- Arquitetura monolítica no padrão MVT (Model-View-Template) do Django

## Estrutura do projeto

```
lojao-do-campinho/
├── lojao_campinho/   # Configurações do projeto (settings.py, urls.py)
├── estoque/          # App responsável pelo controle de estoque
├── manage.py         # Utilitário de linha de comando do Django
└── requirements.txt  # Dependências do projeto
```

## Como rodar o projeto localmente

Os comandos abaixo devem ser executados no terminal, dentro da pasta do projeto.

### 1. Criar o ambiente virtual (apenas na primeira vez)

```bash
python3.12 -m venv .venv
```

### 2. Ativar o ambiente virtual

No macOS ou Linux:

```bash
source .venv/bin/activate
```

No Windows:

```bash
.venv\Scripts\activate
```

Com o ambiente ativo, o nome `(.venv)` aparece no início da linha do terminal.

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Criar o banco de dados

```bash
python manage.py migrate
```

### 5. Criar a conta do dono da loja (apenas na primeira vez)

O sistema não tem cadastro público de usuários. A conta de acesso é criada
pelo terminal:

```bash
python manage.py createsuperuser
```

O comando pede um nome de usuário, um e-mail (opcional) e uma senha.
A senha não aparece enquanto é digitada e é guardada de forma criptografada
(hash) pelo Django. Nunca escreva usuários ou senhas no código do projeto.

Outras contas podem ser criadas depois, pelo painel administrativo em
<http://127.0.0.1:8000/admin/>.

### 6. Iniciar o servidor de desenvolvimento

```bash
python manage.py runserver
```

Depois, acesse <http://127.0.0.1:8000/> no navegador e entre com o usuário
criado no passo 5. Para sair, use o botão **Sair** na barra de navegação.
Para parar o servidor, pressione `Ctrl + C` no terminal.

### 7. Rodar os testes automatizados

```bash
python manage.py test
```

## Integração contínua (GitHub Actions)

**Integração contínua** (CI, do inglês *Continuous Integration*) significa
verificar o projeto automaticamente a cada alteração enviada ao GitHub. Assim,
um erro é descoberto logo, antes de chegar à versão principal.

O arquivo `.github/workflows/django-tests.yml` define essa verificação.
Ela roda automaticamente:

- a cada `push` na branch `main`;
- a cada Pull Request aberto ou atualizado para a branch `main`.

Em uma máquina Linux do GitHub, com Python 3.12 e banco SQLite, ela:

1. instala as dependências do `requirements.txt`;
2. roda `python manage.py check` (verifica a configuração do Django);
3. roda `python manage.py makemigrations --check --dry-run` (confere se não falta nenhuma migração);
4. roda `python manage.py test` (executa todos os testes automatizados).

Para ver os resultados, abra o repositório no GitHub e clique na aba
**Actions**. Cada execução aparece com um ✅ (tudo certo) ou ❌ (algo falhou);
clique nela para ver os detalhes de cada passo. Nos Pull Requests, o resultado
também aparece no final da página, na área de verificações (*checks*).

## Segurança

- Todas as telas exigem login. Quem não está logado é levado à tela de login.
- O login e o logout usam o sistema de autenticação padrão do Django (sessões).
- Todos os formulários enviados por POST usam proteção CSRF (`{% csrf_token %}`).
- O botão **Sair** envia um POST com token CSRF; um simples acesso (GET) não desloga.

### Desenvolvimento x produção

As configurações padrão de `settings.py` são para **desenvolvimento local**.
A `SECRET_KEY` presente no código serve apenas para isso.

Em produção, defina estas variáveis de ambiente:

| Variável | Exemplo | Para que serve |
|---|---|---|
| `DJANGO_SECRET_KEY` | uma chave longa e aleatória | Chave secreta (obrigatória quando `DJANGO_DEBUG=False`) |
| `DJANGO_DEBUG` | `False` | Desliga o modo de depuração |
| `DJANGO_ALLOWED_HOSTS` | `loja.com.br` | Endereços em que o site pode ser acessado |

Com `DJANGO_DEBUG=False`, os cookies de sessão e CSRF passam a ser enviados
apenas por HTTPS. Antes de publicar, rode `python manage.py check --deploy`
para ver as recomendações de segurança do Django.
