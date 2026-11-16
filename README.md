# Lojão do Campinho

Aplicação web simples para controle de estoque de uma pequena papelaria
(loja de material escolar). O objetivo é substituir o controle manual de
estoque por um sistema fácil de usar.

Projeto individual da disciplina de Desenvolvimento de Software.

## Tecnologias

- Python 3.12
- Django 5.2 LTS
- SQLite no desenvolvimento local e PostgreSQL em produção (Render)
- Django Templates, HTML5 e CSS3
- Arquitetura monolítica no padrão MVT (Model-View-Template) do Django
- Gunicorn e WhiteNoise para rodar o site em produção

## Estrutura do projeto

```
lojao-do-campinho/
├── lojao_campinho/   # Configurações do projeto (settings.py, urls.py)
├── estoque/          # App responsável pelo controle de estoque
├── manage.py         # Utilitário de linha de comando do Django
├── requirements.txt  # Dependências do projeto
├── build.sh          # Comandos de build usados pelo Render
└── render.yaml       # Configuração do site e do banco no Render (Blueprint)
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
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://loja.com.br` | Endereços HTTPS de onde os formulários podem ser enviados |
| `DATABASE_URL` | `postgresql://usuario:senha@servidor:5432/banco` | Banco de dados de produção (sem ela, o projeto usa o SQLite) |

Com `DJANGO_DEBUG=False`, os cookies de sessão e CSRF passam a ser enviados
apenas por HTTPS. Antes de publicar, rode `python manage.py check --deploy`
para ver as recomendações de segurança do Django.

No Render, o endereço `*.onrender.com` do site é adicionado automaticamente a
`ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` (pela variável `RENDER_EXTERNAL_HOSTNAME`).
Só é preciso preencher essas duas variáveis se você usar um domínio próprio.

## Deploy no Render

O projeto já vem preparado para o [Render](https://render.com), usando os planos
gratuitos para o site e para o banco PostgreSQL. Nenhuma senha fica no código:
todas as informações secretas são guardadas no painel do Render.

### O que o Render executa

| Etapa | Comando |
|---|---|
| Build | `./build.sh` (instala as dependências, roda `collectstatic`, `migrate` e cria o administrador) |
| Start | `gunicorn lojao_campinho.wsgi:application` |

A versão do Python (3.12) vem do arquivo `.python-version`.

### Passo a passo

1. Crie uma conta gratuita em <https://render.com> e conecte sua conta do GitHub.
2. No painel, clique em **New → Blueprint** e escolha o repositório `lojao-campinho`.
3. O Render lê o arquivo `render.yaml` e mostra o que será criado:
   - um banco **PostgreSQL** gratuito (`lojao-campinho-db`);
   - um **Web Service** gratuito (`lojao-campinho`).
4. Preencha as variáveis pedidas para a conta do dono da loja:
   - `DJANGO_SUPERUSER_USERNAME`: o nome de usuário;
   - `DJANGO_SUPERUSER_EMAIL`: um e-mail;
   - `DJANGO_SUPERUSER_PASSWORD`: uma senha forte (não use a mesma de outros sites).
5. Clique em **Apply** (ou **Deploy Blueprint**) e acompanhe os **Logs** até aparecer
   que o deploy terminou (*Your service is live*).

As outras variáveis são preenchidas pelo próprio Render:

| Variável | De onde vem |
|---|---|
| `DATABASE_URL` | Conexão com o banco `lojao-campinho-db` |
| `DJANGO_SECRET_KEY` | Gerada automaticamente (`generateValue`) |
| `DJANGO_DEBUG` | `False`, definido no `render.yaml` |

### Endereço público do site

Depois do deploy, abra o serviço **lojao-campinho** no painel do Render. O endereço
público aparece no topo da página, no formato `https://lojao-campinho.onrender.com`
(o Render pode acrescentar letras ao nome se ele já estiver em uso). Abra esse
endereço e entre com o usuário e a senha definidos no passo 4.

### Observações sobre o plano gratuito

- O site "dorme" depois de alguns minutos sem acesso. O primeiro acesso depois
  disso pode demorar cerca de um minuto.
- O banco PostgreSQL gratuito do Render tem prazo de validade e limite de espaço.
  Confira as regras atuais do plano gratuito no site do Render antes de usar com
  dados reais.
- A senha do administrador só é usada no primeiro deploy. Para trocá-la depois,
  use o painel `/admin/` do site.
